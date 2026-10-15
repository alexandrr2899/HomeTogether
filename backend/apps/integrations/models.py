"""Links to external entities; the external service keeps the source data."""

from django.conf import settings
from django.db import models


class ExternalEntityLink(models.Model):
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=32)
    purpose = models.CharField(max_length=32)
    entity_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("account", "provider", "purpose"), name="one_external_link_per_purpose"),
            models.UniqueConstraint(fields=("provider", "purpose", "entity_id"), name="one_account_per_external_entity"),
        ]
