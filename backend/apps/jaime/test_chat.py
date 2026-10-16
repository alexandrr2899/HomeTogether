import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .chat_service import run_chat
from .chat_tools import run_tool
from .models import ActionProposal


class FakeOpenClaw:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def complete(self, messages, user_key, tools):
        self.calls.append((messages, user_key, tools))
        return next(self.replies)


class JaimeChatTests(TestCase):
    def setUp(self):
        self.bridge_env = patch.dict(os.environ, {"HT_JAIME_BRIDGE_TOKEN": ""})
        self.bridge_env.start()
        self.addCleanup(self.bridge_env.stop)
        User = get_user_model()
        self.actor = User.objects.create_user("alexander", password="test-only-password", is_staff=True)
        self.viewer = User.objects.create_user("viewer", password="test-only-password")
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1")
        self.client.force_login(self.actor)
        self.client.get("/api/v1/accounts/csrf/")
        self.csrf = self.client.cookies["csrftoken"].value

    def test_unconfigured_chat_is_explicit_and_requires_csrf(self):
        with patch("apps.jaime.views.configured_client", return_value=None):
            self.assertEqual(self.client.get("/api/v1/jaime/chat/").json()["status"], "Sin configurar")
            body = json.dumps({"conversation_id": str(uuid4()), "message": "Hola"})
            self.assertEqual(self.client.post("/api/v1/jaime/chat/", data=body, content_type="application/json").status_code, 403)
            response = self.client.post("/api/v1/jaime/chat/", data=body, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["status"], "Sin configurar")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get("/api/v1/jaime/chat/").status_code, 403)

    def test_tool_call_only_creates_a_pending_proposal(self):
        fake = FakeOpenClaw([
            {"role": "assistant", "content": "", "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "proponer_cambio", "arguments": json.dumps({"tipo": "add_shopping", "nombre": "Compra aislada"})}}]},
            {"role": "assistant", "content": "Preparé una propuesta para que la confirmes."},
        ])
        with patch("apps.jaime.views.configured_client", return_value=fake), patch("apps.jaime.operations.create_item") as external_write:
            conversation_id = uuid4()
            response = self.client.post("/api/v1/jaime/chat/", data=json.dumps({"conversation_id": str(conversation_id), "message": "Añade una compra"}), content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "Conectado")
            self.assertEqual(len(response.json()["proposal_ids"]), 1)
            proposal = ActionProposal.objects.get()
            self.assertEqual(proposal.actor, self.actor)
            self.assertEqual(proposal.state, "pending")
            external_write.assert_not_called()
            self.assertIn(str(conversation_id), fake.calls[0][1])
            self.assertIn(str(self.actor.pk), fake.calls[0][1])
            self.assertEqual(fake.calls[1][0][-1]["role"], "tool")

    def test_invalid_functions_do_not_write_or_escape_actor_scope(self):
        self.assertEqual(run_tool("proponer_cambio", {"tipo": "add_task", "nombre": "", "entity_id": "todo.other"}, self.actor)["status"], "Rechazado")
        self.assertEqual(run_tool("consultar_agenda", {"dias": 365}, self.actor)["status"], "Rechazado")
        self.assertEqual(run_tool("ejecutar_hogar", {"entity_id": "light.all"}, self.actor)["status"], "Rechazado")
        self.assertFalse(ActionProposal.objects.exists())

    def test_presence_read_omits_location_attributes(self):
        with patch("apps.jaime.chat_tools.read_presence", return_value={"status": "Conectado", "people": [{"name": "Alexander", "label": "En casa", "last_updated": "2026-10-15T12:00:00Z", "latitude": 14.0}], "last_checked_at": "2026-10-15T12:01:00Z"}):
            result = run_tool("consultar_presencia", {}, self.actor)
        self.assertNotIn("latitude", result["people"][0])

    def test_wellness_tool_rejects_unknown_person(self):
        result = run_tool("consultar_bienestar", {"persona": "Persona desconocida"}, self.actor)
        self.assertEqual(result["status"], "Rechazado")

    def test_one_message_cannot_create_two_proposals(self):
        calls = [
            {"id": f"call-{index}", "type": "function", "function": {"name": "proponer_cambio", "arguments": json.dumps({"tipo": "add_task", "nombre": "Tarea aislada"})}}
            for index in (1, 2)
        ]
        fake = FakeOpenClaw([{"role": "assistant", "tool_calls": calls}, {"role": "assistant", "content": "Revisa la propuesta."}])
        result = run_chat(fake, self.actor, uuid4(), "Prepara una tarea")
        self.assertEqual(len(result["proposal_ids"]), 1)
        self.assertEqual(ActionProposal.objects.count(), 1)

    def test_django_chat_uses_openclaw_http_protocol_without_external_write(self):
        requests = []

        class Gateway(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def respond(self, payload):
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def do_GET(self):
                requests.append(("GET", self.path, self.headers.get("Authorization"), None))
                self.respond({"data": [{"id": "openclaw/jaime"}]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(("POST", self.path, self.headers.get("Authorization"), body))
                if len([request for request in requests if request[0] == "POST"]) == 1:
                    self.respond({"choices": [{"message": {"role": "assistant", "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "proponer_cambio", "arguments": json.dumps({"tipo": "add_shopping", "nombre": "Compra aislada"})}}]}}]})
                else:
                    self.respond({"choices": [{"message": {"role": "assistant", "content": "Preparé una propuesta para revisar."}}]})

        server = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict(os.environ, {
                "HT_OPENCLAW_URL": f"http://127.0.0.1:{server.server_port}",
                "HT_OPENCLAW_TOKEN": "test-only-token",
                "HT_OPENCLAW_AGENT_ID": "jaime",
            }), patch("apps.jaime.operations.create_item") as external_write:
                self.assertEqual(self.client.get("/api/v1/jaime/chat/").json()["status"], "Conectado")
                response = self.client.post(
                    "/api/v1/jaime/chat/",
                    data=json.dumps({"conversation_id": str(uuid4()), "message": "Prepara una compra"}),
                    content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json()["proposal_ids"]), 1)
                external_write.assert_not_called()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual([request[:2] for request in requests], [
            ("GET", "/v1/models"),
            ("POST", "/v1/chat/completions"),
            ("POST", "/v1/chat/completions"),
        ])
        self.assertTrue(all(request[2] == "Bearer test-only-token" for request in requests))
        self.assertEqual(requests[1][3]["model"], "openclaw/jaime")
        self.assertTrue(requests[1][3]["user"].startswith(f"hometogether:{self.actor.pk}:"))
        self.assertEqual(requests[2][3]["messages"][-1]["role"], "tool")
        self.assertEqual(ActionProposal.objects.count(), 1)
