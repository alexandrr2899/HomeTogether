"""Operational record for an external create; item content stays in Home Assistant."""

import uuid

from django.conf import settings
from django.db import models


class ListCreateOperation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    list_id = models.CharField(max_length=16)
    summary = models.CharField(max_length=255)
    initial_uids = models.JSONField(default=list)
    external_uid = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=16, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
