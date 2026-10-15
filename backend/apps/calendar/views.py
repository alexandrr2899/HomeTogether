import secrets
import time
from datetime import datetime
from html import escape

from django.http import HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from .adapters.google import GoogleCalendarError
from .oauth_flow import OAuthSetupError, authorization_url, exchange_code
from .private_settings import PrivateSettingsError, save_private_setting
from .operations import CalendarOperationError, create_event, delete_event, read_event, update_event
from .serializers import CalendarEventCreateSerializer, CalendarEventUpdateSerializer
from .service import calendar_reader
from .service import _provider


class CalendarEventsView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return super().get_permissions()

    def get(self, request):
        reader = calendar_reader()
        if reader is None:
            return Response({"status": "Sin configurar", "source": "google_calendar", "events": [], "last_checked_at": None})
        try:
            start = datetime.fromisoformat(request.query_params["start"])
            end = datetime.fromisoformat(request.query_params["end"])
            result = reader.events(start, end, request.query_params.get("page_token"))
        except (KeyError, ValueError):
            return Response({"detail": "Indica start y end con zona horaria; máximo 31 días"}, status=400)
        except GoogleCalendarError as error:
            return Response({"status": "Sin conexión", "source": "google_calendar", "events": [], "error": str(error)}, status=503)
        return Response({"status": "Conectado", "source": "google_calendar", **result, "last_checked_at": timezone.now().isoformat()})

    def post(self, request):
        serializer = CalendarEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            event = create_event(serializer.validated_data, request.user.pk)
        except CalendarOperationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        return Response({"status": "Confirmado en Google", "source": "google_calendar", "event": event}, status=201)


class CalendarEventDetailView(APIView):
    def get_permissions(self):
        if self.request.method in {"PATCH", "DELETE"}:
            return [IsAdminUser()]
        return super().get_permissions()

    def get(self, request, event_id):
        try:
            event = read_event(event_id)
        except CalendarOperationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        return Response({"source": "google_calendar", "event": event})

    def patch(self, request, event_id):
        etag = request.headers.get("If-Match", "")
        if not etag or len(etag) > 200:
            return Response({"detail": "Actualiza la agenda para obtener la versión del evento"}, status=400)
        serializer = CalendarEventUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            event = update_event(event_id, serializer.validated_data, etag)
        except CalendarOperationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        return Response({"status": "Confirmado en Google", "source": "google_calendar", "event": event})

    def delete(self, request, event_id):
        etag = request.headers.get("If-Match", "")
        if not etag or len(etag) > 200:
            return Response({"detail": "Actualiza la agenda para obtener la versión del evento"}, status=400)
        try:
            delete_event(event_id, etag)
        except CalendarOperationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        return Response(status=204)


class CalendarOptionsView(APIView):
    def get(self, request):
        reader = calendar_reader("primary")
        if reader is None:
            return Response({"status": "Sin configurar", "calendars": []})
        try:
            result = reader.available_calendars(request.query_params.get("page_token"))
        except GoogleCalendarError as error:
            return Response({"status": "Sin conexión", "calendars": [], "error": str(error)}, status=503)
        return Response({"status": "Conectado", **result})


class OAuthStartView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        state = secrets.token_urlsafe(32)
        try:
            url = authorization_url(state)
        except OAuthSetupError as error:
            return Response({"detail": str(error)}, status=503)
        request.session["google_oauth_state"] = state
        request.session["google_oauth_started"] = time.time()
        response = HttpResponseRedirect(url)
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response


class OAuthCallbackView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        expected = request.session.pop("google_oauth_state", "")
        started = request.session.pop("google_oauth_started", 0)
        received = request.query_params.get("state", "")
        code = request.query_params.get("code", "")
        if (not expected or not isinstance(received, str) or
                not secrets.compare_digest(expected, received) or
                not isinstance(started, (int, float)) or
                time.time() - started > 600 or time.time() < started):
            return Response({"detail": "Estado OAuth inválido o vencido"}, status=400)
        if request.query_params.get("error"):
            request.session["google_oauth_result"] = "No se autorizó el acceso a Google"
        else:
            try:
                refresh_token = exchange_code(code)
                save_private_setting("HT_GOOGLE_REFRESH_TOKEN", refresh_token)
                _provider.cache_clear()
                request.session["google_oauth_result"] = "Google conectado. Selecciona el calendario familiar."
            except (OAuthSetupError, PrivateSettingsError) as error:
                request.session["google_oauth_result"] = str(error)
        response = HttpResponseRedirect("/api/v1/calendar/oauth/result/")
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response


class OAuthResultView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        message = request.session.pop("google_oauth_result", "Sin datos")
        options = ""
        reader = calendar_reader("primary")
        if reader is not None:
            try:
                available = []
                page_token = None
                seen_tokens = set()
                while True:
                    page = reader.available_calendars(page_token)
                    available.extend(page["calendars"])
                    page_token = page.get("next_page_token")
                    if not page_token:
                        break
                    if page_token in seen_tokens or len(seen_tokens) >= 20:
                        raise GoogleCalendarError("Paginación de calendarios no válida")
                    seen_tokens.add(page_token)
                writable = [item for item in available if item.get("accessRole") in {"owner", "writer"}]
                choices = "".join(
                    f"<option value='{escape(item['id'], quote=True)}'>{escape(item.get('summary', item['id']))} "
                    f"({escape(item['accessRole'])})</option>"
                    for item in writable if item.get("id")
                )
                if choices:
                    options = (
                        "<h2>Seleccionar calendario familiar</h2>"
                        "<form method='post' action='/api/v1/calendar/select/'>"
                        f"<input type='hidden' name='csrfmiddlewaretoken' value='{escape(get_token(request), quote=True)}'>"
                        "<label for='calendar'>Calendario</label><br>"
                        "<select id='calendar' name='calendar_id' required>"
                        "<option value=''>Elige un calendario</option>"
                        f"{choices}</select> <button type='submit'>Seleccionar</button></form>"
                    )
                else:
                    options = "<p>Sin calendarios con permisos de escritura.</p>"
            except GoogleCalendarError:
                options = "<p>No se pudo consultar la lista de calendarios. Inténtalo de nuevo.</p>"
        response = HttpResponse(
            "<!doctype html><html lang='es'><meta charset='utf-8'>"
            "<meta name='referrer' content='same-origin'>"
            "<title>Home Together</title><body style='font-family:system-ui;max-width:34rem;margin:4rem auto;padding:1rem'>"
            f"<h1>Home Together</h1><p>{escape(message)}</p>{options}"
            "<p>Vuelve a la aplicación para continuar.</p></body></html>"
        )
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "same-origin"
        return response


class CalendarSelectView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        calendar_id = request.data.get("calendar_id", "")
        if not isinstance(calendar_id, str) or not calendar_id or len(calendar_id) > 1024:
            return Response({"detail": "Selecciona un calendario válido"}, status=400)
        reader = calendar_reader(calendar_id)
        if reader is None:
            return Response({"detail": "Google sin configurar"}, status=503)
        try:
            metadata = reader.calendar_metadata()
        except GoogleCalendarError as error:
            return Response({"detail": str(error)}, status=503)
        if metadata.get("access_role") not in {"owner", "writer"} or not metadata.get("id"):
            return Response({"detail": "La cuenta no puede gestionar todos los eventos de ese calendario"}, status=403)
        try:
            save_private_setting("HT_GOOGLE_CALENDAR_ID", metadata["id"])
        except PrivateSettingsError as error:
            return Response({"detail": str(error)}, status=503)
        if request.content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
            request.session["google_oauth_result"] = "Calendario familiar seleccionado."
            return HttpResponseRedirect("/api/v1/calendar/oauth/result/")
        return Response({"status": "Seleccionado", "calendar": metadata})
