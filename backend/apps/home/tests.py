from unittest.mock import patch
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.integrations.models import ExternalEntityLink

from .presence import read_presence
from .models import WellnessPreference
from .wellness import read_wellness


class PresenceTests(TestCase):
    def test_no_mapping_reports_unconfigured_without_calling_ha(self):
        with patch("apps.home.presence.configured_home_assistant_client") as client:
            result = read_presence()
        self.assertEqual(result["status"], "Sin configurar")
        self.assertEqual(result["people"], [])
        client.assert_not_called()

    def test_only_mapped_person_states_are_returned_without_location(self):
        user = get_user_model().objects.create_user("alexander", first_name="Alexander", password="test-only-password")
        ExternalEntityLink.objects.create(account=user, provider="home_assistant", purpose="presence", entity_id="person.alexandrr")

        class FakeClient:
            def get(self, path):
                self.path = path
                return {
                    "entity_id": "person.alexandrr", "state": "home",
                    "last_updated": "2026-10-15T12:00:00Z",
                    "attributes": {"latitude": 14.0, "longitude": -87.0, "source": "device_tracker.phone"},
                }

        client = FakeClient()
        with patch("apps.home.presence.configured_home_assistant_client", return_value=client):
            result = read_presence()
        self.assertEqual(client.path, "/api/states/person.alexandrr")
        self.assertEqual(result["people"][0]["label"], "En casa")
        self.assertNotIn("latitude", str(result))
        self.assertNotIn("longitude", str(result))
        self.assertNotIn("device_tracker", str(result))

    def test_presence_api_requires_session(self):
        response = Client().get("/api/v1/home/presence/")
        self.assertIn(response.status_code, (401, 403))


class WellnessPrivacyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alexander = User.objects.create_user("alexander", first_name="Alexander", password="test-only-password", is_staff=True)
        self.lastenia = User.objects.create_user("lastenia", first_name="Lastenia", password="test-only-password", is_staff=True)
        for purpose, suffix in (("wellness_steps", "steps"), ("wellness_sleep", "sleep_duration"), ("wellness_activity", "last_activity")):
            ExternalEntityLink.objects.create(account=self.alexander, provider="home_assistant", purpose=purpose, entity_id=f"sensor.garmin_connect_{suffix}")

    def fake_state(self, path):
        entity_id = path.removeprefix("/api/states/")
        values = {"steps": ("100", "steps"), "sleep_duration": ("420", "min"), "last_activity": ("Actividad privada", None), "body_battery": ("65", "%")}
        suffix = entity_id.removeprefix("sensor.garmin_connect_")
        value, unit = values[suffix]
        return {"entity_id": entity_id, "state": value, "last_updated": "2026-10-15T14:00:00Z", "attributes": {"unit_of_measurement": unit, "startTime": "2026-10-14T12:00:00Z", "startLatitude": 14.0, "startLongitude": -87.0}}

    def test_owner_only_by_default_and_no_location_attributes(self):
        with patch("apps.home.wellness.configured_home_assistant_client") as client:
            client.return_value.get.side_effect = self.fake_state
            own = read_wellness(self.alexander, self.alexander)
            other = read_wellness(self.alexander, self.lastenia)
            assistant = read_wellness(self.alexander, self.alexander, for_jaime=True)
        self.assertEqual(set(own["metrics"]), {"steps", "sleep", "activity"})
        self.assertEqual(own["metrics"]["steps"]["value"], 100)
        self.assertEqual(other["metrics"], {})
        self.assertEqual(assistant["metrics"], {})
        self.assertEqual(client.return_value.get.call_count, 3)
        self.assertNotIn("Latitude", str(own))
        self.assertNotIn("Longitude", str(own))
        self.assertNotIn("entity_id", str(own))

    def test_owner_can_share_individual_metric_without_granting_jaime(self):
        client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1")
        client.force_login(self.alexander)
        client.get("/api/v1/accounts/csrf/")
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.patch("/api/v1/home/wellness/preferences/", data=json.dumps({"shared_metrics": ["steps"]}), content_type="application/json").status_code, 403)
        response = client.patch("/api/v1/home/wellness/preferences/", data=json.dumps({"shared_metrics": ["steps"]}), content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["allow_jaime"])
        client.force_login(self.lastenia)
        with patch("apps.home.wellness.configured_home_assistant_client") as source:
            source.return_value.get.side_effect = self.fake_state
            shared = client.get("/api/v1/home/wellness/shared/")
        self.assertEqual(shared.status_code, 200)
        self.assertEqual(set(shared.json()[0]["metrics"]), {"steps"})
        self.assertFalse(WellnessPreference.objects.get(account=self.alexander).allow_jaime)
        self.assertEqual(client.get("/api/v1/home/wellness/me/").json()["status"], "Sin configurar")

    def test_selection_changes_own_metrics_without_exposing_unknown_sensors(self):
        client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1")
        client.force_login(self.alexander)
        client.get("/api/v1/accounts/csrf/")
        token = client.cookies["csrftoken"].value
        path = "/api/v1/home/wellness/preferences/"
        invalid = client.patch(path, data=json.dumps({"visible_metrics": ["steps", "last_activity_route"]}), content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(invalid.status_code, 400)
        invalid_share = client.patch(path, data=json.dumps({"shared_metrics": ["body_battery"]}), content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(invalid_share.status_code, 400)
        saved = client.patch(path, data=json.dumps({"visible_metrics": ["steps", "body_battery"], "shared_metrics": ["body_battery"]}), content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["visible_metrics"], ["steps", "body_battery"])
        with patch("apps.home.wellness.configured_home_assistant_client") as source:
            source.return_value.get.side_effect = self.fake_state
            own = client.get("/api/v1/home/wellness/me/")
            self.assertEqual(set(own.json()["metrics"]), {"steps", "body_battery"})
            self.assertEqual(source.return_value.get.call_count, 2)
        client.force_login(self.lastenia)
        with patch("apps.home.wellness.configured_home_assistant_client") as source:
            source.return_value.get.side_effect = self.fake_state
            shared = client.get("/api/v1/home/wellness/shared/")
        self.assertEqual(set(shared.json()[0]["metrics"]), {"body_battery"})
        self.assertFalse(WellnessPreference.objects.get(account=self.alexander).allow_jaime)

    def test_catalog_only_returns_reviewed_metadata(self):
        client = Client(HTTP_HOST="127.0.0.1")
        client.force_login(self.alexander)
        with patch("apps.home.wellness.configured_home_assistant_client") as source:
            source.return_value.get.return_value = [self.fake_state("/api/states/sensor.garmin_connect_steps"), self.fake_state("/api/states/sensor.garmin_connect_body_battery")]
            response = client.get("/api/v1/home/wellness/catalog/")
        self.assertEqual(response.status_code, 200)
        stats = {item["key"]: item for item in response.json()["stats"]}
        self.assertTrue(stats["steps"]["available"])
        self.assertTrue(stats["body_battery"]["available"])
        self.assertFalse(stats["sleep"]["available"])
        self.assertNotIn("Latitude", str(response.json()))
        self.assertNotIn("value", str(response.json()))
