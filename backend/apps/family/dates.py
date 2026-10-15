from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser

from .models import FamilyProfile, ImportantDate
from .serializers import ImportantDateSerializer


class ImportantDatesView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = ImportantDateSerializer

    def get_queryset(self):
        return ImportantDate.objects.filter(profile_id=self.kwargs["profile_id"]).order_by("date", "id")

    def perform_create(self, serializer):
        profile = get_object_or_404(FamilyProfile, pk=self.kwargs["profile_id"])
        serializer.save(profile=profile)


class ImportantDateDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = ImportantDateSerializer
    lookup_url_kwarg = "date_id"

    def get_queryset(self):
        return ImportantDate.objects.filter(profile_id=self.kwargs["profile_id"])
