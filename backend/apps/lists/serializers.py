import uuid

from rest_framework import serializers


class ListItemCreateSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    summary = serializers.CharField(max_length=255, trim_whitespace=True)


class ListItemUpdateSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=255, trim_whitespace=True, required=False)
    status = serializers.ChoiceField(choices=("needs_action", "completed"), required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Indica un cambio")
        return attrs
