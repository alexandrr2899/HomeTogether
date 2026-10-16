import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ActionProposal(models.Model):
    KINDS = (("add_task", "Añadir tarea"), ("add_shopping", "Añadir compra"), ("complete_task", "Completar tarea"))
    STATES = (("pending", "Pendiente"), ("confirmed", "Confirmada"), ("uncertain", "Resultado incierto"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, choices=KINDS)
    payload = models.JSONField()
    state = models.CharField(max_length=12, choices=STATES, default="pending")
    result = models.JSONField(default=dict, blank=True)
    error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)


class BridgeTurn(models.Model):
    """Short-lived server-side binding between one chat turn and its account."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()
    calls = models.PositiveSmallIntegerField(default=0)
    last_tool = models.CharField(max_length=32, blank=True)
    proposal = models.OneToOneField(ActionProposal, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
