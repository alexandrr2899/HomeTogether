"""Small, explicit input contract for events written to Google Calendar."""

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from rest_framework import serializers


APP_ZONE = ZoneInfo("America/Tegucigalpa")
RECURRENCE = re.compile(r"^RRULE:FREQ=(DAILY|WEEKLY);COUNT=([1-9][0-9]?)$")


def _endpoint(value: object):
    if not isinstance(value, dict):
        raise serializers.ValidationError("La fecha debe ser un objeto")
    if set(value) == {"date"}:
        try:
            return "all_day", date.fromisoformat(value["date"])
        except (TypeError, ValueError):
            raise serializers.ValidationError("Fecha de día completo no válida") from None
    if set(value) == {"dateTime", "timeZone"} and value["timeZone"] == "America/Tegucigalpa":
        try:
            parsed = datetime.fromisoformat(value["dateTime"])
        except (TypeError, ValueError):
            raise serializers.ValidationError("Hora no válida") from None
        if parsed.tzinfo is None or parsed.utcoffset() != APP_ZONE.utcoffset(parsed):
            raise serializers.ValidationError("La hora debe incluir el desplazamiento de America/Tegucigalpa")
        return "timed", parsed
    raise serializers.ValidationError("Usa date o dateTime con America/Tegucigalpa")


class CalendarEventFieldsSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=200, required=False, allow_blank=False)
    start = serializers.JSONField(required=False)
    end = serializers.JSONField(required=False)
    location = serializers.CharField(max_length=500, required=False, allow_blank=True)
    description = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    recurrence = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, attrs):
        if ("start" in attrs) != ("end" in attrs):
            raise serializers.ValidationError("Indica inicio y fin juntos")
        if "start" in attrs:
            start_kind, start = _endpoint(attrs["start"])
            end_kind, end = _endpoint(attrs["end"])
            if start_kind != end_kind or end <= start:
                raise serializers.ValidationError("El fin debe ser posterior y del mismo tipo")
            if end - start > timedelta(days=31):
                raise serializers.ValidationError("El evento no puede durar más de 31 días")
            if "recurrence" in attrs and start_kind != "timed":
                raise serializers.ValidationError("La recurrencia requiere una hora")
        if "recurrence" in attrs:
            values = attrs["recurrence"]
            if len(values) != 1 or not RECURRENCE.fullmatch(values[0]) or int(RECURRENCE.fullmatch(values[0]).group(2)) > 52:
                raise serializers.ValidationError("Recurrencia no admitida")
        return attrs


class CalendarEventCreateSerializer(CalendarEventFieldsSerializer):
    operation_id = serializers.UUIDField()
    summary = serializers.CharField(max_length=200, allow_blank=False)
    start = serializers.JSONField()
    end = serializers.JSONField()


class CalendarEventUpdateSerializer(CalendarEventFieldsSerializer):
    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Indica al menos un cambio")
        return super().validate(attrs)
