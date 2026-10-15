import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import ListCreateOperation
from .operations import ListOperationError, create_item, delete_item, update_item


class _FakeListClient:
    def __init__(self, items=None, apply=True):
        self.items = list(items or [])
        self.apply = apply
        self.calls = []

    def todo_items(self, entity_id, status):
        return [item.copy() for item in self.items if item["status"] == status]

    def todo_action(self, action, entity_id, **fields):
        self.calls.append((action, entity_id, fields))
        if not self.apply:
            return
        if action == "add_item":
            self.items.append({"uid": "new-uid", "summary": fields["item"].lower(), "status": "needs_action"})
        elif action == "update_item":
            item = next(row for row in self.items if row["uid"] == fields["item"])
            if "rename" in fields:
                item["summary"] = fields["rename"]
            if "status" in fields:
                item["status"] = fields["status"]
        elif action == "remove_item":
            self.items = [row for row in self.items if row["uid"] != fields["item"]]


class ListOperationTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user("list-tester", password="test-only-password")
        self.entity = "todo.test_list"

    def test_create_confirms_external_uid_and_replay_does_not_add_again(self):
        client = _FakeListClient()
        operation_id = uuid.uuid4()
        with patch("apps.lists.operations._context", return_value=(client, self.entity)):
            item = create_item("compras", operation_id, "Manzanas", self.actor)
            replay = create_item("compras", operation_id, "Manzanas", self.actor)
        self.assertEqual(item["uid"], "new-uid")
        self.assertEqual(replay["uid"], "new-uid")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(ListCreateOperation.objects.get(pk=operation_id).state, "confirmed")

    def test_uncertain_create_is_not_sent_again(self):
        client = _FakeListClient(apply=False)
        operation_id = uuid.uuid4()
        with patch("apps.lists.operations._context", return_value=(client, self.entity)), patch("apps.lists.operations.time.sleep"):
            with self.assertRaises(ListOperationError):
                create_item("compras", operation_id, "Manzanas", self.actor)
            with self.assertRaises(ListOperationError):
                create_item("compras", operation_id, "Manzanas", self.actor)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(ListCreateOperation.objects.get(pk=operation_id).state, "uncertain")

    def test_existing_name_blocks_creation(self):
        client = _FakeListClient([{"uid": "personal", "summary": "Manzanas", "status": "needs_action"}])
        with patch("apps.lists.operations._context", return_value=(client, self.entity)):
            with self.assertRaises(ListOperationError):
                create_item("compras", uuid.uuid4(), "manzanas", self.actor)
        self.assertEqual(client.calls, [])

    def test_update_and_delete_use_uid_then_confirm_external_state(self):
        client = _FakeListClient([{"uid": "external-1", "summary": "Manzanas", "status": "needs_action"}])
        with patch("apps.lists.operations._context", return_value=(client, self.entity)):
            updated = update_item("compras", "external-1", {"status": "completed"})
            delete_item("compras", "external-1")
        self.assertEqual(updated["status"], "completed")
        self.assertEqual([call[2]["item"] for call in client.calls], ["external-1", "external-1"])
        self.assertEqual(client.items, [])


class ListWriteApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("ordinary", password="test-only-password")
        self.admin = get_user_model().objects.create_user("administrator", password="test-only-password", is_staff=True)
        self.client = Client(enforce_csrf_checks=True)
        self.path = "/api/v1/lists/compras/items/"

    def test_anonymous_and_non_admin_cannot_create(self):
        body = '{"operation_id":"00000000-0000-4000-8000-000000000001","summary":"Prueba"}'
        response = self.client.post(self.path, body, content_type="application/json")
        self.assertIn(response.status_code, (401, 403))
        self.client.force_login(self.user)
        response = self.client.post(self.path, body, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_admin_requires_csrf_and_uses_the_selected_list(self):
        body = '{"operation_id":"00000000-0000-4000-8000-000000000001","summary":"Prueba"}'
        self.client.force_login(self.admin)
        response = self.client.post(self.path, body, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.client.get("/api/v1/accounts/csrf/")
        token = self.client.cookies["csrftoken"].value
        with patch("apps.lists.views.create_item", return_value={"uid": "uid-1", "summary": "Prueba", "status": "needs_action"}) as create:
            response = self.client.post(self.path, body, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(create.call_args.args[0], "compras")
        self.assertEqual(create.call_args.args[2], "Prueba")
