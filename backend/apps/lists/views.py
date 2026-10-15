from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser

from django.utils import timezone

from .service import read_lists
from .operations import ListOperationError, create_item, delete_item, update_item
from .serializers import ListItemCreateSerializer, ListItemUpdateSerializer


class ListsView(APIView):
    def get(self, request):
        lists = read_lists()
        statuses = {item["status"] for item in lists}
        status = "Conectado" if "Conectado" in statuses else (
            "Sin conexión" if "Sin conexión" in statuses else "Sin configurar"
        )
        return Response({
            "status": status,
            "lists": lists,
            "last_checked_at": timezone.now().isoformat(),
        })


class ListItemsView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, list_id):
        serializer = ListItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = create_item(list_id, serializer.validated_data["operation_id"],
                               serializer.validated_data["summary"], request.user)
        except ListOperationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        return Response({"status": "Confirmado en Home Assistant", "item": item}, status=201)


class ListItemDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, list_id, uid):
        serializer = ListItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = update_item(list_id, uid, serializer.validated_data)
        except ListOperationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        return Response({"status": "Confirmado en Home Assistant", "item": item})

    def delete(self, request, list_id, uid):
        try:
            delete_item(list_id, uid)
        except ListOperationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        return Response(status=204)
