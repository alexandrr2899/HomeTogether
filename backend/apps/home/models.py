from django.conf import settings
from django.db import models

from .garmin_catalog import default_visible_stats


class WellnessPreference(models.Model):
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wellness_preference")
    visible_metrics = models.JSONField(default=default_visible_stats)
    shared_metrics = models.JSONField(default=list)
    allow_jaime = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
