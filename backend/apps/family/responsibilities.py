from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import FamilyProfile, Responsibility
from .serializers import ResponsibilitySerializer
from .references import resolve_reference


class ResponsibilitiesView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = ResponsibilitySerializer

    def get_queryset(self):
        return Responsibility.objects.filter(profile_id=self.kwargs["profile_id"]).order_by("due_date", "id")

    def perform_create(self, serializer):
        profile = get_object_or_404(FamilyProfile, pk=self.kwargs["profile_id"])
        serializer.save(profile=profile)


class ResponsibilityDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = ResponsibilitySerializer
    lookup_url_kwarg = "responsibility_id"

    def get_queryset(self):
        return Responsibility.objects.filter(profile_id=self.kwargs["profile_id"])


class ResponsibilitySourceView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, profile_id, responsibility_id):
        responsibility = get_object_or_404(Responsibility, pk=responsibility_id, profile_id=profile_id)
        if not responsibility.external_source or not responsibility.external_id:
            return Response({"status": "Sin configurar"})
        return Response(resolve_reference(responsibility.external_source, responsibility.external_id))
