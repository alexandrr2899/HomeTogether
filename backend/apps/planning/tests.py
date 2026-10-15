import json
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .models import Ingredient, MenuEntry, Recipe, Trip, TripDocument


class PlanningApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("planner", password="test-only-password", is_staff=True)
        self.visitor = User.objects.create_user("visitor", password="test-only-password")
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1")

    def login(self):
        self.client.force_login(self.admin)
        self.client.get("/api/v1/accounts/csrf/")
        return self.client.cookies["csrftoken"].value

    def post_json(self, path, data, token):
        return self.client.post(path, data=json.dumps(data), content_type="application/json", HTTP_X_CSRFTOKEN=token)

    def test_private_empty_and_csrf(self):
        self.assertIn(self.client.get("/api/v1/planning/recipes/").status_code, (401, 403))
        self.client.force_login(self.visitor)
        self.assertEqual(self.client.get("/api/v1/planning/trips/").status_code, 403)
        token = self.login()
        self.assertEqual(self.client.get("/api/v1/planning/recipes/").json(), [])
        self.assertEqual(self.client.get("/api/v1/planning/trips/").json(), [])
        self.assertEqual(self.client.post("/api/v1/planning/recipes/", data="{}", content_type="application/json").status_code, 403)
        self.assertTrue(token)

    def test_recipe_menu_and_preview_never_write_to_shopping(self):
        token = self.login()
        recipe = self.post_json("/api/v1/planning/recipes/", {
            "title": "Receta aislada", "instructions": "Preparar", "servings": 2,
            "ingredients": [{"name": "Tomate", "amount": "2", "position": 0}, {"name": "Pan", "amount": "1", "position": 1}],
        }, token)
        self.assertEqual(recipe.status_code, 201)
        recipe_id = recipe.json()["id"]
        self.assertEqual(Ingredient.objects.filter(recipe_id=recipe_id).count(), 2)
        self.assertEqual(self.post_json("/api/v1/planning/menu/", {
            "date": "2026-10-15", "meal": "almuerzo", "recipe": recipe_id, "notes": "",
        }, token).status_code, 201)
        url = "/api/v1/planning/menu/shopping-preview/?start=2026-10-12&end=2026-10-18"
        with patch("apps.planning.menu.configured_client") as client, patch("apps.planning.menu.entity_for_list", return_value="todo.test"):
            client.return_value.todo_items.side_effect = lambda entity, status: [{"summary": "2 tomate", "status": status}] if status == "needs_action" else []
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            items = {item["summary"]: item for item in response.json()["items"]}
            self.assertEqual(items["2 Tomate"]["already_on_list"], True)
            self.assertEqual(items["1 Pan"]["already_on_list"], False)
            client.return_value.todo_add_item.assert_not_called()
        self.assertEqual(MenuEntry.objects.count(), 1)
        self.assertEqual(self.client.get("/api/v1/planning/menu/?start=nope&end=2026-10-18").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/v1/planning/recipes/{recipe_id}/", HTTP_X_CSRFTOKEN=token).status_code, 400)

    def test_trip_preparations_and_private_document(self):
        token = self.login()
        response = self.post_json("/api/v1/planning/trips/", {
            "title": "Viaje aislado", "destination": "Prueba", "start_date": "2026-10-15", "end_date": "2026-10-14", "notes": "",
        }, token)
        self.assertEqual(response.status_code, 400)
        response = self.post_json("/api/v1/planning/trips/", {
            "title": "Viaje aislado", "destination": "Prueba", "start_date": "2026-10-15", "end_date": "2026-10-16", "notes": "",
        }, token)
        self.assertEqual(response.status_code, 201)
        trip_id = response.json()["id"]
        self.assertEqual(self.post_json(f"/api/v1/planning/trips/{trip_id}/preparations/", {"title": "Preparar"}, token).status_code, 201)
        self.assertEqual(self.post_json(f"/api/v1/planning/trips/{trip_id}/participants/", {"name": "Persona de prueba"}, token).status_code, 201)
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            upload = SimpleUploadedFile("reserva.pdf", b"private-trip-test", content_type="application/pdf")
            response = self.client.post(f"/api/v1/planning/trips/{trip_id}/documents/", {"file": upload}, HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 201)
            document_id = response.json()["id"]
            document = TripDocument.objects.get(pk=document_id)
            self.assertFalse(document.file.name.endswith(".pdf"))
            download = self.client.get(f"/api/v1/planning/trips/{trip_id}/documents/{document_id}/")
            self.assertEqual(download.status_code, 200)
            self.assertEqual(b"".join(download.streaming_content), b"private-trip-test")
            self.client.force_login(self.visitor)
            self.assertEqual(self.client.get(f"/api/v1/planning/trips/{trip_id}/documents/{document_id}/").status_code, 403)
        self.assertEqual(Trip.objects.count(), 1)
