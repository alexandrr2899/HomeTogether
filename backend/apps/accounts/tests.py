import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class PrivateApiTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = get_user_model().objects.create_user(username="tester", password="local-test-password")

    def test_private_data_requires_session(self):
        paths = (
            "/api/v1/accounts/me/",
            "/api/v1/family/status/",
            "/api/v1/integrations/connections/",
            "/api/v1/calendar/events/",
            "/api/v1/lists/",
            "/api/v1/home/presence/",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_login_requires_csrf_and_uses_session(self):
        body = json.dumps({"username": "tester", "password": "local-test-password"})
        url = "/api/v1/accounts/login/"
        self.assertEqual(self.client.post(url, body, content_type="application/json").status_code, 403)
        self.client.get("/api/v1/accounts/csrf/")
        csrf_token = self.client.cookies["csrftoken"].value
        response = self.client.post(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/accounts/me/").status_code, 200)
        csrf_token = self.client.cookies["csrftoken"].value
        response = self.client.post("/api/v1/accounts/logout/", HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/accounts/me/").status_code, 403)
