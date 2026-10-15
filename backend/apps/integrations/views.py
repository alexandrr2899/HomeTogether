import os

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.calendar.adapters.google import GoogleCalendarError
from apps.calendar.service import calendar_reader
from apps.jaime.openclaw_client import OpenClawError, configured_client
from .adapters.home_assistant import HomeAssistantClient, HomeAssistantError
from .status import google_calendar_status, home_assistant_status, home_assistant_web_url


class ConnectionsView(APIView):
    def get(self, request):
        google_status = google_calendar_status()
        google_error = None
        google_checked = None
        if google_status != "Sin configurar":
            google_checked = timezone.now().isoformat()
            try:
                reader = calendar_reader()
                metadata = reader.calendar_metadata() if reader else {}
                if reader and metadata.get("id") == reader.calendar_id:
                    google_status = "Conectado"
                else:
                    google_status = "Sin conexión"
                    google_error = "No se pudo confirmar el calendario seleccionado"
            except GoogleCalendarError:
                google_status = "Sin conexión"
                google_error = "No se pudo consultar Google Calendar"
        ha_status = home_assistant_status()
        ha_error = None
        ha_checked = None
        if ha_status != "Sin configurar":
            ha_checked = timezone.now().isoformat()
            try:
                client = HomeAssistantClient(
                    os.environ["HOME_ASSISTANT_URL"],
                    os.environ["HOME_ASSISTANT_TOKEN"],
                    os.environ.get("CLOUDFLARE_ACCESS_CLIENT_ID", ""),
                    os.environ.get("CLOUDFLARE_ACCESS_CLIENT_SECRET", ""),
                )
                ha_status = "Conectado" if client.ping() else "Sin conexión"
            except (HomeAssistantError, ValueError) as exc:
                ha_status = "Sin conexión"
                ha_error = str(exc)
        openclaw_status = "Sin configurar"
        openclaw_error = None
        openclaw_checked = None
        try:
            openclaw = configured_client()
            if openclaw is not None:
                openclaw_checked = timezone.now().isoformat()
                openclaw_status = "Conectado" if openclaw.probe() else "Sin conexión"
                if openclaw_status == "Sin conexión":
                    openclaw_error = "El agente Jaime no está disponible en OpenClaw"
        except OpenClawError:
            openclaw_status = "Sin conexión"
            openclaw_error = "No se pudo consultar OpenClaw"
        return Response({"connections": [
            {"service": "google_calendar", "status": google_status, "last_sync": google_checked, "error": google_error},
            {"service": "home_assistant", "status": ha_status, "last_sync": ha_checked, "error": ha_error,
             "web_url": home_assistant_web_url()},
            {"service": "openclaw", "status": openclaw_status, "last_sync": openclaw_checked, "error": openclaw_error},
        ]})
