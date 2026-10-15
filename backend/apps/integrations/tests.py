from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from .status import home_assistant_web_url


class HomeAssistantBrowserLinkTests(SimpleTestCase):
    def test_link_contains_only_safe_https_origin(self):
        with patch.dict("os.environ", {"HOME_ASSISTANT_URL": "https://ordcast.tempaques.com/api/"}):
            self.assertEqual(home_assistant_web_url(), "https://ordcast.tempaques.com/")

    def test_rejects_credentials_and_query_in_link(self):
        for address in (
            "http://ordcast.tempaques.com/",
            "https://user:secret@ordcast.tempaques.com/",
            "https://ordcast.tempaques.com/?token=secret",
        ):
            with self.subTest(address=address), patch.dict("os.environ", {"HOME_ASSISTANT_URL": address}):
                self.assertIsNone(home_assistant_web_url())


class ConnectionStatusTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("viewer", password="test-only-password"))

    @patch("apps.integrations.views.home_assistant_status", return_value="Sin configurar")
    @patch("apps.integrations.views.google_calendar_status", return_value="Sin configurar")
    def test_openclaw_only_reports_connected_after_a_live_probe(self, _google, _home):
        with patch("apps.integrations.views.configured_client", return_value=None):
            connections = self.client.get("/api/v1/integrations/connections/").json()["connections"]
        self.assertEqual(connections[-1]["service"], "openclaw")
        self.assertEqual(connections[-1]["status"], "Sin configurar")
        self.assertIsNone(connections[-1]["last_sync"])

        with patch("apps.integrations.views.configured_client") as client:
            client.return_value.probe.return_value = False
            connection = self.client.get("/api/v1/integrations/connections/").json()["connections"][-1]
        self.assertEqual(connection["status"], "Sin conexión")
        self.assertIsNotNone(connection["last_sync"])
