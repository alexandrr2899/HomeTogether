from django.db import transaction
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser

from .models import FamilyProfile
from .serializers import FamilyProfileSerializer


class FamilyProfilesView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = FamilyProfileSerializer
    queryset = FamilyProfile.objects.prefetch_related("important_dates", "responsibilities", "documents").order_by("name", "id")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class FamilyProfileDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = FamilyProfileSerializer
    queryset = FamilyProfile.objects.prefetch_related("important_dates", "responsibilities", "documents")

    def perform_destroy(self, instance):
        paths = [document.file.name for document in instance.documents.all()]
        storage = instance.documents.model._meta.get_field("file").storage
        with transaction.atomic():
            instance.delete()
            transaction.on_commit(lambda: [storage.delete(path) for path in paths])
