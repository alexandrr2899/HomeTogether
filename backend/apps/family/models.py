"""Home Together's own family information; no external list or calendar copies."""

import uuid

from django.conf import settings
from django.db import models


class FamilyProfile(models.Model):
    name = models.CharField(max_length=160)
    relationship = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    birthday = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ImportantDate(models.Model):
    profile = models.ForeignKey(FamilyProfile, related_name="important_dates", on_delete=models.CASCADE)
    label = models.CharField(max_length=120)
    date = models.DateField()
    repeats_annually = models.BooleanField(default=True)


class Responsibility(models.Model):
    profile = models.ForeignKey(FamilyProfile, related_name="responsibilities", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    external_source = models.CharField(max_length=40, blank=True)
    external_id = models.CharField(max_length=255, blank=True)


def private_document_path(instance, filename):
    return f"family/{uuid.uuid4().hex}"


class PrivateDocument(models.Model):
    profile = models.ForeignKey(FamilyProfile, related_name="documents", on_delete=models.CASCADE)
    file = models.FileField(upload_to=private_document_path)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
