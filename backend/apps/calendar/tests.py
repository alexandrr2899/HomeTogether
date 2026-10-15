import io
import json
import os
import stat
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from .adapters.google import GoogleCalendarReader
from .adapters.google_write import GoogleCalendarWriter
from .adapters.google_write import GoogleCalendarWriteError
from .adapters.oauth import RefreshTokenProvider
from .oauth_flow import OAuthSetupError, SCOPES, authorization_url, exchange_code
from .private_settings import save_private_setting
from .operations import CalendarOperationError, create_event, delete_event, update_event
from .serializers import CalendarEventCreateSerializer


class _Response:
    def __init__(self, payload):
        self.content = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self.content

    def __exit__(self, *args):
        self.content.close()


class _Opener:
    def __init__(self, payload):
        self.payload = payload
        self.request = None
        self.calls = 0

    def open(self, request, timeout):
        self.request = request
        self.calls += 1
        return _Response(self.payload)


class GoogleReaderTests(SimpleTestCase):
    def test_reads_bounded_window_and_keeps_external_id(self):
        reader = GoogleCalendarReader("family@example.com", lambda: "local-test-token")
        opener = _Opener({
            "items": [{"id": "external-1", "summary": "test", "start": {"date": "2026-10-14"}, "end": {"date": "2026-10-15"}}],
            "timeZone": "America/Tegucigalpa",
            "nextPageToken": "next",
        })
        reader._opener = opener
        start = datetime(2026, 10, 14, tzinfo=ZoneInfo("America/Tegucigalpa"))
        result = reader.events(start, start + timedelta(days=1))
        self.assertEqual(result["events"][0]["id"], "external-1")
        self.assertEqual(result["next_page_token"], "next")
        self.assertIn("family%40example.com", opener.request.full_url)
        self.assertIn("timeZone=America%2FTegucigalpa", opener.request.full_url)

    def test_rejects_unbounded_or_naive_window(self):
        reader = GoogleCalendarReader("family@example.com", lambda: "local-test-token")
        start = datetime(2026, 10, 14, tzinfo=ZoneInfo("America/Tegucigalpa"))
        with self.assertRaises(ValueError):
            reader.events(start, start + timedelta(days=32))
        with self.assertRaises(ValueError):
            reader.events(datetime(2026, 10, 14), datetime(2026, 10, 15))


class GoogleWriterTests(SimpleTestCase):
    def test_create_requires_stable_id_and_sends_selected_calendar_only(self):
        writer = GoogleCalendarWriter("family@example.com", lambda: "local-test-token")
        opener = _Opener({"id": "a12345", "etag": '"v1"'})
        writer._opener = opener
        with self.assertRaises(ValueError):
            writer.create_event({"summary": "Temporal", "start": {"date": "2026-10-17"}, "end": {"date": "2026-10-18"}})
        result = writer.create_event({"id": "a12345", "summary": "Temporal", "start": {"date": "2026-10-17"}, "end": {"date": "2026-10-18"}})
        self.assertEqual(result["id"], "a12345")
        self.assertEqual(opener.request.get_method(), "POST")
        self.assertIn("/calendars/family%40example.com/events", opener.request.full_url)
        self.assertNotIn("local-test-token", opener.request.full_url)

    def test_update_and_delete_require_etag(self):
        writer = GoogleCalendarWriter("family@example.com", lambda: "local-test-token")
        opener = _Opener({"id": "a12345", "etag": '"v2"'})
        writer._opener = opener
        with self.assertRaises(ValueError):
            writer.update_event("a12345", {"id": "a12345"}, "")
        writer.update_event("a12345", {"id": "a12345", "summary": "Editado"}, '"v1"')
        self.assertEqual(opener.request.get_method(), "PUT")
        self.assertEqual(opener.request.get_header("If-match"), '"v1"')
        with self.assertRaises(ValueError):
            writer.delete_event("a12345", "")
        writer.delete_event("a12345", '"v2"')
        self.assertEqual(opener.request.get_method(), "DELETE")
        self.assertEqual(opener.request.get_header("If-match"), '"v2"')


class CalendarOperationTests(SimpleTestCase):
    def test_create_reuses_stable_google_id_after_uncertain_response(self):
        class Writer:
            calendar_id = "family@example.com"

            def __init__(self):
                self.event = None
                self.calls = 0

            def calendar_metadata(self):
                return {"id": self.calendar_id, "access_role": "owner"}

            def get_event(self, event_id):
                return self.event

            def create_event(self, event):
                self.calls += 1
                self.event = {**event, "etag": '"v1"', "status": "confirmed"}
                raise GoogleCalendarWriteError("timeout", uncertain=True)

        writer = Writer()
        data = {
            "operation_id": uuid.uuid4(), "summary": "Evento real",
            "start": {"date": "2026-10-17"}, "end": {"date": "2026-10-18"},
        }
        with patch("apps.calendar.operations.calendar_writer", return_value=writer):
            first = create_event(data, 7)
            second = create_event(data, 7)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(writer.calls, 1)

    def test_create_rejects_reused_operation_for_different_data(self):
        class Writer:
            calendar_id = "family@example.com"

            def calendar_metadata(self):
                return {"id": self.calendar_id, "access_role": "owner"}

            def get_event(self, event_id):
                return {"id": event_id, "summary": "Anterior", "start": {"date": "2026-10-17"}, "end": {"date": "2026-10-18"}}

        data = {"operation_id": uuid.uuid4(), "summary": "Diferente", "start": {"date": "2026-10-17"}, "end": {"date": "2026-10-18"}}
        with patch("apps.calendar.operations.calendar_writer", return_value=Writer()):
            with self.assertRaises(CalendarOperationError) as error:
                create_event(data, 7)
        self.assertEqual(error.exception.status_code, 409)

    def test_create_validates_dates_and_bounded_recurrence(self):
        base = {
            "operation_id": str(uuid.uuid4()), "summary": "Prueba",
            "start": {"dateTime": "2026-10-18T12:00:00-06:00", "timeZone": "America/Tegucigalpa"},
            "end": {"dateTime": "2026-10-18T12:10:00-06:00", "timeZone": "America/Tegucigalpa"},
            "recurrence": ["RRULE:FREQ=DAILY;COUNT=2"],
        }
        self.assertTrue(CalendarEventCreateSerializer(data=base).is_valid())
        self.assertFalse(CalendarEventCreateSerializer(data={**base, "recurrence": ["RRULE:FREQ=DAILY"]}).is_valid())
        self.assertFalse(CalendarEventCreateSerializer(data={**base, "end": {"dateTime": "2026-10-18T12:10:00Z", "timeZone": "America/Tegucigalpa"}}).is_valid())

    def test_update_rejects_stale_etag_before_writing(self):
        class Writer:
            calendar_id = "family@example.com"

            def calendar_metadata(self):
                return {"id": self.calendar_id, "access_role": "owner"}

            def get_event(self, event_id):
                return {"id": event_id, "etag": '"new"', "summary": "Actual"}

            def update_event(self, *args):
                raise AssertionError("No se debe escribir con un ETag antiguo")

        with patch("apps.calendar.operations.calendar_writer", return_value=Writer()):
            with self.assertRaises(CalendarOperationError) as error:
                update_event("a12345", {"summary": "Propuesta"}, '"old"')
        self.assertEqual(error.exception.status_code, 409)

    def test_delete_accepts_google_cancelled_tombstone(self):
        class Writer:
            calendar_id = "family@example.com"

            def __init__(self):
                self.deleted = False

            def calendar_metadata(self):
                return {"id": self.calendar_id, "access_role": "owner"}

            def get_event(self, event_id):
                return {"id": event_id, "etag": '"v1"', "status": "cancelled" if self.deleted else "confirmed"}

            def delete_event(self, event_id, etag):
                self.deleted = True

        writer = Writer()
        with patch("apps.calendar.operations.calendar_writer", return_value=writer):
            delete_event("a12345", '"v1"')
        self.assertTrue(writer.deleted)


class OAuthRefreshTests(SimpleTestCase):
    def test_refreshes_once_and_keeps_credentials_in_request_body(self):
        provider = RefreshTokenProvider("test-client", "test-secret", "test-refresh")
        opener = _Opener({"access_token": "test-access", "expires_in": 3600})
        provider._opener = opener
        self.assertEqual(provider(), "test-access")
        self.assertEqual(provider(), "test-access")
        self.assertEqual(opener.calls, 1)
        self.assertIn(b"grant_type=refresh_token", opener.request.data)
        self.assertIn(b"refresh_token=test-refresh", opener.request.data)
        self.assertNotIn("test-refresh", opener.request.full_url)


@override_settings(GOOGLE_REDIRECT_URI="http://127.0.0.1:8005/api/v1/calendar/oauth/callback/")
class OAuthSetupTests(SimpleTestCase):
    def test_authorization_requests_only_calendar_list_and_events(self):
        with patch.dict(os.environ, {"HT_GOOGLE_CLIENT_ID": "test-id", "HT_GOOGLE_CLIENT_SECRET": "test-secret"}):
            url = authorization_url("test-state")
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["redirect_uri"], ["http://127.0.0.1:8005/api/v1/calendar/oauth/callback/"])
        self.assertEqual(set(query["scope"][0].split()), set(SCOPES))
        self.assertEqual(query["access_type"], ["offline"])
        self.assertEqual(query["state"], ["test-state"])
        self.assertNotIn("test-secret", url)

    def test_private_refresh_token_file_has_restricted_permissions(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("HT_GOOGLE_REFRESH_TOKEN=old\nHT_GOOGLE_CLIENT_ID=test-id\n")
            with patch.dict(os.environ, {}, clear=False):
                save_private_setting("HT_GOOGLE_REFRESH_TOKEN", "test-new", path)
            self.assertEqual(path.read_text().count("HT_GOOGLE_REFRESH_TOKEN="), 1)
            self.assertIn("HT_GOOGLE_REFRESH_TOKEN=test-new", path.read_text())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_code_exchange_checks_granted_scopes(self):
        opener = _Opener({"refresh_token": "test-refresh", "scope": SCOPES[0]})
        with patch.dict(os.environ, {"HT_GOOGLE_CLIENT_ID": "test-id", "HT_GOOGLE_CLIENT_SECRET": "test-secret"}):
            with self.assertRaises(OAuthSetupError):
                exchange_code("test-code", opener)
        self.assertIn(b"grant_type=authorization_code", opener.request.data)
        self.assertNotIn("test-code", opener.request.full_url)


@override_settings(GOOGLE_REDIRECT_URI="http://127.0.0.1:8005/api/v1/calendar/oauth/callback/")
class OAuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = get_user_model().objects.create_user(username="test-admin", password="local-test-only", is_staff=True)

    def test_start_requires_admin_and_uses_session_state(self):
        self.assertEqual(self.client.get("/api/v1/calendar/oauth/start/").status_code, 403)
        self.client.force_login(self.admin)
        with patch.dict(os.environ, {"HT_GOOGLE_CLIENT_ID": "test-id", "HT_GOOGLE_CLIENT_SECRET": "test-secret"}):
            response = self.client.get("/api/v1/calendar/oauth/start/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("https://accounts.google.com/"))
        self.assertEqual(parse_qs(urlsplit(response["Location"]).query)["state"], [self.client.session["google_oauth_state"]])

    def test_callback_rejects_wrong_state_without_exchanging_code(self):
        self.client.force_login(self.admin)
        session = self.client.session
        session["google_oauth_state"] = "expected"
        session["google_oauth_started"] = __import__("time").time()
        session.save()
        with patch("apps.calendar.views.exchange_code") as exchange:
            response = self.client.get("/api/v1/calendar/oauth/callback/?state=wrong&code=test-code")
        self.assertEqual(response.status_code, 400)
        exchange.assert_not_called()

    def test_callback_stores_refresh_token_server_side_only(self):
        self.client.force_login(self.admin)
        session = self.client.session
        session["google_oauth_state"] = "expected"
        session["google_oauth_started"] = __import__("time").time()
        session.save()
        with patch("apps.calendar.views.exchange_code", return_value="test-refresh"), \
             patch("apps.calendar.views.save_private_setting") as save:
            response = self.client.get("/api/v1/calendar/oauth/callback/?state=expected&code=test-code")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/api/v1/calendar/oauth/result/")
        save.assert_called_once_with("HT_GOOGLE_REFRESH_TOKEN", "test-refresh")
        self.assertNotIn(b"test-refresh", response.content)

    def test_result_shows_only_writable_calendar_choices(self):
        self.client.force_login(self.admin)

        class Reader:
            def available_calendars(self, page_token=None):
                return {"calendars": [
                    {"id": "family@example.com", "summary": "Familiar", "accessRole": "owner"},
                    {"id": "private@example.com", "summary": "Privado", "accessRole": "reader"},
                ]}

        with patch("apps.calendar.views.calendar_reader", return_value=Reader()):
            response = self.client.get("/api/v1/calendar/oauth/result/")
        self.assertContains(response, "family@example.com")
        self.assertNotContains(response, "private@example.com")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertEqual(response["Referrer-Policy"], "same-origin")

    def test_result_includes_writable_calendars_from_later_pages(self):
        self.client.force_login(self.admin)

        class Reader:
            def available_calendars(self, page_token=None):
                if page_token is None:
                    return {"calendars": [], "next_page_token": "page-2"}
                return {"calendars": [
                    {"id": "family@example.com", "summary": "Familiar", "accessRole": "writer"},
                ], "next_page_token": None}

        with patch("apps.calendar.views.calendar_reader", return_value=Reader()):
            response = self.client.get("/api/v1/calendar/oauth/result/")
        self.assertContains(response, "family@example.com")

    def test_selection_rejects_calendar_without_write_access(self):
        self.client.force_login(self.admin)

        class Reader:
            def calendar_metadata(self):
                return {"id": "private@example.com", "access_role": "reader", "time_zone": "America/Tegucigalpa"}

        with patch("apps.calendar.views.calendar_reader", return_value=Reader()), \
             patch("apps.calendar.views.save_private_setting") as save:
            response = self.client.post("/api/v1/calendar/select/", json.dumps({"calendar_id": "private@example.com"}), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        save.assert_not_called()


class CalendarWriteViewTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.admin = get_user_model().objects.create_user(username="calendar-admin", password="local-test-only", is_staff=True)
        self.member = get_user_model().objects.create_user(username="calendar-member", password="local-test-only")
        self.body = json.dumps({
            "operation_id": str(uuid.uuid4()), "summary": "Prueba",
            "start": {"date": "2026-10-17"}, "end": {"date": "2026-10-18"},
        })

    def test_create_requires_admin_and_csrf_then_confirms_google_result(self):
        url = "/api/v1/calendar/events/"
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(url, self.body, content_type="application/json").status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(url, self.body, content_type="application/json").status_code, 403)
        self.client.get("/api/v1/accounts/csrf/")
        token = self.client.cookies["csrftoken"].value
        with patch("apps.calendar.views.create_event", return_value={"id": "a12345", "etag": '"v1"'}) as create:
            response = self.client.post(url, self.body, content_type="application/json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="http://testserver")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["event"]["id"], "a12345")
        create.assert_called_once()

    def test_update_requires_etag(self):
        self.client.force_login(self.admin)
        self.client.get("/api/v1/accounts/csrf/")
        token = self.client.cookies["csrftoken"].value
        response = self.client.patch(
            "/api/v1/calendar/events/a12345/", json.dumps({"summary": "Editado"}),
            content_type="application/json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="http://testserver",
        )
        self.assertEqual(response.status_code, 400)
