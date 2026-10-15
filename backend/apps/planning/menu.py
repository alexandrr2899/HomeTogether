from datetime import date, timedelta

from django.utils import timezone
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.adapters.home_assistant import HomeAssistantError
from apps.lists.service import configured_client, entity_for_list, items_for_entity

from .models import MenuEntry
from .serializers import MenuEntrySerializer


def window(request):
    if "start" not in request.query_params and "end" not in request.query_params:
        start = timezone.localdate()
        return start, start + timedelta(days=6)
    try:
        start = date.fromisoformat(request.query_params["start"])
        end = date.fromisoformat(request.query_params["end"])
    except (KeyError, ValueError):
        raise ValueError("Indica un intervalo de fechas válido")
    if end < start or (end - start).days > 13:
        raise ValueError("El intervalo del menú debe ser de hasta 14 días")
    return start, end


class MenuEntriesView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = MenuEntrySerializer

    def get_queryset(self):
        start, end = window(self.request)
        return MenuEntry.objects.select_related("recipe").filter(date__gte=start, date__lte=end)

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except ValueError as error:
            return Response({"detail": str(error)}, status=400)


class MenuEntryDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = MenuEntrySerializer
    queryset = MenuEntry.objects.select_related("recipe")


class ShoppingPreviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            start, end = window(request)
        except ValueError as error:
            return Response({"detail": str(error)}, status=400)
        entries = MenuEntry.objects.select_related("recipe").prefetch_related("recipe__ingredients").filter(
            date__gte=start, date__lte=end,
        )
        candidates = {}
        for entry in entries:
            for ingredient in entry.recipe.ingredients.all():
                summary = f"{ingredient.amount.strip()} {ingredient.name.strip()}".strip()
                key = summary.casefold()
                if key not in candidates:
                    candidates[key] = {"summary": summary, "occurrences": 0, "already_on_list": False}
                candidates[key]["occurrences"] += 1
        if not candidates:
            return Response({"status": "Sin datos", "shopping_status": "Sin datos", "items": [], "last_checked_at": timezone.now().isoformat()})
        try:
            entity_id = entity_for_list("compras")
            current = items_for_entity(configured_client(), entity_id)
            existing = {item.get("summary", "").casefold() for item in current}
            shopping_status = "Conectado"
            for key, candidate in candidates.items():
                candidate["already_on_list"] = key in existing
        except (KeyError, ValueError, HomeAssistantError):
            shopping_status = "Sin conexión"
        return Response({
            "status": "Conectado", "shopping_status": shopping_status,
            "items": list(candidates.values()), "last_checked_at": timezone.now().isoformat(),
        })
