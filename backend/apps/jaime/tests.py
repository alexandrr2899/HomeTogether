import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.lists.operations import ListOperationError

from .models import ActionProposal


class ProposalTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alexander = User.objects.create_user("alexander", password="test-only-password", is_staff=True)
        self.lastenia = User.objects.create_user("lastenia", password="test-only-password", is_staff=True)
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1")
        self.client.force_login(self.alexander)
        self.client.get("/api/v1/accounts/csrf/")
        self.csrf = self.client.cookies["csrftoken"].value

    def test_proposal_requires_separate_confirm_and_only_its_author_can_confirm(self):
        with patch("apps.jaime.operations.create_item") as create:
            response = self.client.post("/api/v1/jaime/proposals/", data=json.dumps({"kind": "add_shopping", "payload": {"summary": "Compra aislada"}}), content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf)
            self.assertEqual(response.status_code, 201)
            proposal_id = response.json()["id"]
            self.assertEqual(response.json()["state"], "pending")
            create.assert_not_called()
            self.assertEqual(self.client.post(f"/api/v1/jaime/proposals/{proposal_id}/confirm/").status_code, 403)
            self.client.force_login(self.lastenia)
            self.assertEqual(self.client.post(f"/api/v1/jaime/proposals/{proposal_id}/confirm/", HTTP_X_CSRFTOKEN=self.csrf).status_code, 404)
            self.client.force_login(self.alexander)
            self.client.get("/api/v1/accounts/csrf/")
            token = self.client.cookies["csrftoken"].value
            create.return_value = {"uid": "external-uid", "summary": "Compra aislada", "status": "needs_action"}
            confirmed = self.client.post(f"/api/v1/jaime/proposals/{proposal_id}/confirm/", HTTP_X_CSRFTOKEN=token)
            self.assertEqual(confirmed.status_code, 200)
            self.assertEqual(confirmed.json()["state"], "confirmed")
            self.assertEqual(create.call_count, 1)
            self.assertEqual(self.client.post(f"/api/v1/jaime/proposals/{proposal_id}/confirm/", HTTP_X_CSRFTOKEN=token).status_code, 409)
            self.assertEqual(create.call_count, 1)

    def test_invalid_payload_cannot_create_action(self):
        response = self.client.post("/api/v1/jaime/proposals/", data=json.dumps({"kind": "add_task", "payload": {"summary": "", "entity_id": "todo.other"}}), content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ActionProposal.objects.exists())

    def test_uncertain_external_result_is_recorded_and_not_resent(self):
        proposal = ActionProposal.objects.create(actor=self.alexander, kind="add_task", payload={"summary": "Tarea aislada"})
        with patch("apps.jaime.operations.create_item", side_effect=ListOperationError("Sin confirmación", 503)) as create:
            url = f"/api/v1/jaime/proposals/{proposal.id}/confirm/"
            self.assertEqual(self.client.post(url, HTTP_X_CSRFTOKEN=self.csrf).status_code, 503)
            proposal.refresh_from_db()
            self.assertEqual(proposal.state, "uncertain")
            self.assertEqual(self.client.post(url, HTTP_X_CSRFTOKEN=self.csrf).status_code, 409)
            self.assertEqual(create.call_count, 1)
