import uuid

from django.conf import settings
from django.db import models

from apps.family.models import FamilyProfile


class Trip(models.Model):
    title = models.CharField(max_length=180)
    destination = models.CharField(max_length=180, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TripParticipant(models.Model):
    trip = models.ForeignKey(Trip, related_name="participants", on_delete=models.CASCADE)
    profile = models.ForeignKey(FamilyProfile, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=160)


class TripPreparation(models.Model):
    trip = models.ForeignKey(Trip, related_name="preparations", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    done = models.BooleanField(default=False)


def trip_document_path(instance, filename):
    return f"trips/{uuid.uuid4().hex}"


class TripDocument(models.Model):
    trip = models.ForeignKey(Trip, related_name="documents", on_delete=models.CASCADE)
    file = models.FileField(upload_to=trip_document_path)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
