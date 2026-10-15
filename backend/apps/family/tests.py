import json
import os
import stat
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .models import FamilyProfile, PrivateDocument
from .references import resolve_reference


class FamilyApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("alexander", password="test-only-password", is_staff=True)
        self.other = User.objects.create_user("visitor", password="test-only-password")
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1")

    def _admin_session(self):
        self.client.force_login(self.admin)
        self.client.get("/api/v1/accounts/csrf/")
        return self.client.cookies["csrftoken"].value

    def test_profiles_start_empty_and_require_admin(self):
        self.assertFalse(FamilyProfile.objects.exists())
        self.assertIn(self.client.get("/api/v1/family/profiles/").status_code, (401, 403))
        self.client.force_login(self.other)
        self.assertEqual(self.client.get("/api/v1/family/profiles/").status_code, 403)
        self._admin_session()
        response = self.client.get("/api/v1/family/profiles/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_profile_and_date_can_be_created_without_a_parent_account(self):
        token = self._admin_session()
        response = self.client.post(
            "/api/v1/family/profiles/",
            data=json.dumps({"name": "Persona de prueba", "relationship": "Familiar"}),
            content_type="application/json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 201)
        profile_id = response.json()["id"]
        self.assertEqual(FamilyProfile.objects.get(pk=profile_id).created_by, self.admin)
        response = self.client.post(
            f"/api/v1/family/profiles/{profile_id}/dates/",
            data=json.dumps({"label": "Fecha de prueba", "date": "2026-10-15", "repeats_annually": False}),
            content_type="application/json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.get(f"/api/v1/family/profiles/{profile_id}/")
        self.assertEqual(len(response.json()["important_dates"]), 1)

    def test_private_document_is_admin_only_and_downloaded_as_attachment(self):
        token = self._admin_session()
        profile = FamilyProfile.objects.create(name="Persona de prueba", created_by=self.admin)
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            upload = SimpleUploadedFile("registro.pdf", b"private-test-content", content_type="application/pdf")
            response = self.client.post(
                f"/api/v1/family/profiles/{profile.pk}/documents/",
                data={"file": upload}, HTTP_X_CSRFTOKEN=token,
            )
            self.assertEqual(response.status_code, 201)
            document = PrivateDocument.objects.get(pk=response.json()["id"])
            self.assertFalse(document.file.name.endswith(".pdf"))
            self.assertEqual(stat.S_IMODE(os.stat(document.file.path).st_mode), 0o600)
            download = self.client.get(f"/api/v1/family/profiles/{profile.pk}/documents/{document.pk}/")
            self.assertEqual(download.status_code, 200)
            self.assertIn("attachment", download["Content-Disposition"])
            self.assertEqual(b"".join(download.streaming_content), b"private-test-content")
            self.client.force_login(self.other)
            forbidden = self.client.get(f"/api/v1/family/profiles/{profile.pk}/documents/{document.pk}/")
            self.assertEqual(forbidden.status_code, 403)

    def test_responsibility_links_verified_source_without_creating_external_item(self):
        token = self._admin_session()
        profile = FamilyProfile.objects.create(name="Persona de prueba", created_by=self.admin)
        path = f"/api/v1/family/profiles/{profile.pk}/responsibilities/"
        data = {"title": "Responsabilidad de prueba", "external_source": "home_assistant_todo", "external_id": "tareas:uid-123"}
        with patch("apps.family.serializers.resolve_reference", return_value={"status": "Sin datos"}):
            unavailable = self.client.post(path, data=json.dumps(data), content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(unavailable.status_code, 400)
        self.assertFalse(profile.responsibilities.exists())
        with patch("apps.family.serializers.resolve_reference", return_value={"status": "Conectado", "title": "Tarea real"}) as source:
            forbidden = self.client.post(path, data=json.dumps(data), content_type="application/json")
            self.assertEqual(forbidden.status_code, 403)
            created = self.client.post(path, data=json.dumps(data), content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(created.status_code, 201)
        source.assert_called_once_with("home_assistant_todo", "tareas:uid-123")
        responsibility = profile.responsibilities.get()
        self.assertEqual(responsibility.external_id, data["external_id"])
        with patch("apps.family.responsibilities.resolve_reference", return_value={"status": "Conectado", "kind": "tarea", "title": "Tarea editada", "item_status": "needs_action"}):
            response = self.client.get(f"{path}{responsibility.pk}/source/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Tarea editada")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"{path}{responsibility.pk}/source/").status_code, 403)

    def test_only_general_task_list_can_be_linked(self):
        with patch("apps.family.references.configured_client") as source:
            self.assertEqual(resolve_reference("home_assistant_todo", "compras:uid-123")["status"], "Sin configurar")
        source.assert_not_called()
