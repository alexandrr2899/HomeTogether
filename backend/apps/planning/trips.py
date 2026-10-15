from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser

from .models import Trip, TripParticipant, TripPreparation
from .serializers import TripParticipantSerializer, TripPreparationSerializer, TripSerializer


class TripsView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TripSerializer
    queryset = Trip.objects.prefetch_related("participants", "preparations", "documents").order_by("start_date", "id")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TripDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TripSerializer
    queryset = Trip.objects.prefetch_related("participants", "preparations", "documents")

    def perform_destroy(self, instance):
        paths = [document.file.name for document in instance.documents.all()]
        storage = instance.documents.model._meta.get_field("file").storage
        with transaction.atomic():
            instance.delete()
            transaction.on_commit(lambda: [storage.delete(path) for path in paths])


class TripParticipantsView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TripParticipantSerializer

    def get_queryset(self):
        return TripParticipant.objects.filter(trip_id=self.kwargs["trip_id"]).order_by("id")

    def perform_create(self, serializer):
        serializer.save(trip=get_object_or_404(Trip, pk=self.kwargs["trip_id"]))


class TripParticipantDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TripParticipantSerializer
    lookup_url_kwarg = "participant_id"

    def get_queryset(self):
        return TripParticipant.objects.filter(trip_id=self.kwargs["trip_id"])


class TripPreparationsView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TripPreparationSerializer

    def get_queryset(self):
        return TripPreparation.objects.filter(trip_id=self.kwargs["trip_id"]).order_by("id")

    def perform_create(self, serializer):
        serializer.save(trip=get_object_or_404(Trip, pk=self.kwargs["trip_id"]))


class TripPreparationDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = TripPreparationSerializer
    lookup_url_kwarg = "preparation_id"

    def get_queryset(self):
        return TripPreparation.objects.filter(trip_id=self.kwargs["trip_id"])
