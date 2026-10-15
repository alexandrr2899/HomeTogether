from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FamilyProfile


class FamilyStatusView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        count = FamilyProfile.objects.count()
        return Response({"status": "Con datos" if count else "Sin datos", "profile_count": count})
