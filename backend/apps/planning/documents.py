from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Trip, TripDocument
from .serializers import TripDocumentSerializer


MAX_DOCUMENT_SIZE = 15 * 1024 * 1024


class TripDocumentsView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser]

    def get(self, request, trip_id):
        documents = TripDocument.objects.filter(trip_id=trip_id).order_by("-uploaded_at", "-id")
        return Response(TripDocumentSerializer(documents, many=True).data)

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, pk=trip_id)
        upload = request.FILES.get("file")
        if upload is None or upload.size == 0 or upload.size > MAX_DOCUMENT_SIZE:
            return Response({"detail": "Selecciona un archivo de hasta 15 MB"}, status=400)
        original_name = upload.name.replace("\\", "/").rsplit("/", 1)[-1]
        if not original_name or len(original_name) > 255 or any(ord(char) < 32 for char in original_name):
            return Response({"detail": "Nombre de archivo no válido"}, status=400)
        document = TripDocument.objects.create(
            trip=trip, file=upload, original_name=original_name,
            size=upload.size, uploaded_by=request.user,
        )
        return Response(TripDocumentSerializer(document).data, status=201)


class TripDocumentDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, trip_id, document_id):
        document = get_object_or_404(TripDocument, pk=document_id, trip_id=trip_id)
        try:
            stream = document.file.open("rb")
        except OSError:
            return Response({"detail": "El archivo ya no está disponible"}, status=404)
        response = FileResponse(stream, as_attachment=True, filename=document.original_name, content_type="application/octet-stream")
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def delete(self, request, trip_id, document_id):
        document = get_object_or_404(TripDocument, pk=document_id, trip_id=trip_id)
        storage = document.file.storage
        path = document.file.name
        with transaction.atomic():
            document.delete()
            transaction.on_commit(lambda: storage.delete(path))
        return Response(status=204)
