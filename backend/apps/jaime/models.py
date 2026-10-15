import uuid

from django.conf import settings
from django.db import models


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
