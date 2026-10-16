import json
import os
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .bridge import execute_bridge
from .models import ActionProposal, BridgeTurn


TOKEN = "test-only-bridge-token-with-more-than-32-characters"
PATH = "/api/v1/jaime/bridge/"


class BridgeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alexander = User.objects.create_user("alexander", password="test-only-password", is_staff=True)
        self.lastenia = User.objects.create_user("lastenia", password="test-only-password", is_staff=True)
        self.turn = BridgeTurn.objects.create(actor=self.lastenia, expires_at=timezone.now() + timedelta(minutes=3))
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1")
        self.payload = {"turn_id": str(self.turn.pk), "tool": "consultar_lista", "arguments": {"lista": "compras"}}

    def request(self, payload=None, token=TOKEN):
        return self.client.post(PATH, data=json.dumps(self.payload if payload is None else payload),
                                content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}")

    @patch.dict(os.environ, {"HT_JAIME_BRIDGE_TOKEN": TOKEN})
    def test_service_token_and_turn_bind_read_to_actor(self):
        with patch("apps.jaime.bridge.run_tool", return_value={"status": "Conectado", "items": []}) as tool:
            self.assertEqual(self.client.post(PATH, data=json.dumps(self.payload), content_type="application/json").status_code, 403)
            self.assertEqual(self.request(token="incorrect").status_code, 403)
            response = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "Conectado")
        tool.assert_called_once_with("consultar_lista", {"lista": "compras"}, self.lastenia)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.calls, 1)
        self.assertEqual(self.turn.last_tool, "consultar_lista")

    @patch.dict(os.environ, {"HT_JAIME_BRIDGE_TOKEN": TOKEN})
    def test_rejects_unapproved_actions_unknown_turn_expiry_and_excess_calls(self):
        with patch("apps.jaime.bridge.run_tool") as tool:
            self.assertEqual(self.request({**self.payload, "tool": "ejecutar_hogar"}).status_code, 400)
            self.assertEqual(self.request({**self.payload, "turn_id": str(uuid4())}).status_code, 403)
            self.assertEqual(self.request({**self.payload, "tool": []}).status_code, 400)
            self.turn.calls = 6
            self.turn.save(update_fields=["calls"])
            self.assertEqual(self.request().status_code, 429)
            self.turn.expires_at = timezone.now() - timedelta(seconds=1)
            self.turn.save(update_fields=["expires_at"])
            self.assertEqual(self.request().status_code, 403)
        tool.assert_not_called()

    @patch.dict(os.environ, {"HT_JAIME_BRIDGE_TOKEN": TOKEN})
    def test_one_pending_proposal_per_turn_without_external_write(self):
        payload = {"turn_id": str(self.turn.pk), "tool": "proponer_cambio",
                   "arguments": {"tipo": "add_shopping", "nombre": "Compra de prueba aislada"}}
        with patch("apps.jaime.operations.create_item") as external_write:
            first = self.request(payload)
            second = self.request({**payload, "arguments": {"tipo": "add_task", "nombre": "Otra propuesta"}})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "Pendiente de confirmación")
        self.assertEqual(second.json()["proposal_id"], first.json()["proposal_id"])
        self.assertEqual(ActionProposal.objects.count(), 1)
        self.assertEqual(ActionProposal.objects.get().actor, self.lastenia)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.calls, 1)
        self.assertEqual(self.turn.proposal_id, ActionProposal.objects.get().pk)
        external_write.assert_not_called()

    @patch.dict(os.environ, {"HT_JAIME_BRIDGE_TOKEN": TOKEN})
    def test_account_permission_change_blocks_remaining_turn(self):
        self.lastenia.is_staff = False
        self.lastenia.save(update_fields=["is_staff"])
        with patch("apps.jaime.bridge.run_tool") as tool:
            self.assertEqual(self.request().status_code, 403)
        tool.assert_not_called()

    @patch.dict(os.environ, {"HT_JAIME_BRIDGE_TOKEN": TOKEN})
    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_private_host_request_works_with_production_ssl_settings(self):
        with patch("apps.jaime.bridge.run_tool", return_value={"status": "Conectado"}):
            response = self.client.post(PATH, data=json.dumps(self.payload), content_type="application/json",
                                        HTTP_AUTHORIZATION=f"Bearer {TOKEN}", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, {"HT_JAIME_BRIDGE_TOKEN": TOKEN})
    def test_chat_creates_and_closes_turn(self):
        class FakeOpenClaw:
            calls = []

            def complete(self, messages, user_key, tools):
                self.calls.append((messages, tools))
                return {"role": "assistant", "content": "Hola."}

        fake = FakeOpenClaw()
        self.client.force_login(self.alexander)
        self.client.get("/api/v1/accounts/csrf/")
        csrf = self.client.cookies["csrftoken"].value
        with patch("apps.jaime.views.configured_client", return_value=fake):
            response = self.client.post("/api/v1/jaime/chat/", data=json.dumps({"conversation_id": str(uuid4()), "message": "Hola"}),
                                        content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(fake.calls[0][1], [])
        self.assertIn("skill hometogether", fake.calls[0][0][0]["content"])
        self.assertEqual(BridgeTurn.objects.count(), 2)
        new_turn = BridgeTurn.objects.exclude(pk=self.turn.pk).get()
        self.assertEqual(new_turn.actor, self.alexander)
        self.assertLessEqual(new_turn.expires_at, timezone.now())

    @patch.dict(os.environ, {"HT_JAIME_BRIDGE_TOKEN": TOKEN})
    def test_chat_returns_pending_proposal_created_by_bridge(self):
        class FakeOpenClaw:
            def complete(self, messages, user_key, tools):
                turn = BridgeTurn.objects.order_by("-created_at").first()
                result, status = execute_bridge(turn.pk, "proponer_cambio", {"tipo": "add_task", "nombre": "Tarea aislada"})
                assert status == 200 and result.get("proposal_id")
                return {"role": "assistant", "content": "Preparé una propuesta pendiente."}

        self.client.force_login(self.alexander)
        self.client.get("/api/v1/accounts/csrf/")
        csrf = self.client.cookies["csrftoken"].value
        with patch("apps.jaime.views.configured_client", return_value=FakeOpenClaw()), patch("apps.jaime.operations.create_item") as external_write:
            response = self.client.post("/api/v1/jaime/chat/", data=json.dumps({"conversation_id": str(uuid4()), "message": "Prepara una tarea"}),
                                        content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["proposal_ids"]), 1)
        self.assertEqual(ActionProposal.objects.get().state, "pending")
        self.assertEqual(ActionProposal.objects.get().actor, self.alexander)
        external_write.assert_not_called()
