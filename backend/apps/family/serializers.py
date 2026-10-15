from rest_framework import serializers

from .models import FamilyProfile, ImportantDate, PrivateDocument, Responsibility
from .references import resolve_reference


class ImportantDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportantDate
        fields = ("id", "label", "date", "repeats_annually")


class ResponsibilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsibility
        fields = ("id", "title", "notes", "due_date", "external_source", "external_id")

    def validate(self, attrs):
        current = self.instance
        source = attrs.get("external_source", current.external_source if current else "")
        external_id = attrs.get("external_id", current.external_id if current else "")
        if bool(source) != bool(external_id):
            raise serializers.ValidationError("El origen y el identificador externo deben indicarse juntos")
        if source and source not in {"google_calendar", "home_assistant_todo"}:
            raise serializers.ValidationError("Origen externo no admitido")
        if source and (not current or source != current.external_source or external_id != current.external_id):
            result = resolve_reference(source, external_id)
            if result["status"] != "Conectado":
                raise serializers.ValidationError({"external_id": "No se pudo confirmar el elemento en su servicio de origen"})
        return attrs


class PrivateDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivateDocument
        fields = ("id", "original_name", "size", "uploaded_at")


class FamilyProfileSerializer(serializers.ModelSerializer):
    important_dates = ImportantDateSerializer(many=True, read_only=True)
    responsibilities = ResponsibilitySerializer(many=True, read_only=True)
    documents = PrivateDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = FamilyProfile
        fields = (
            "id", "name", "relationship", "phone", "email", "birthday", "notes",
            "important_dates", "responsibilities", "documents", "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
