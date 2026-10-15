from rest_framework import serializers

from .models import ActionProposal


class ActionProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionProposal
        fields = ("id", "kind", "payload", "state", "result", "error", "created_at", "confirmed_at")
        read_only_fields = ("id", "state", "result", "error", "created_at", "confirmed_at")

    def validate(self, attrs):
        kind = attrs["kind"]
        payload = attrs["payload"]
        if not isinstance(payload, dict):
            raise serializers.ValidationError({"payload": "Formato no válido"})
        if kind in {"add_task", "add_shopping"}:
            summary = payload.get("summary")
            if set(payload) != {"summary"} or not isinstance(summary, str) or not summary.strip() or len(summary.strip()) > 255:
                raise serializers.ValidationError({"payload": "Indica un nombre de hasta 255 caracteres"})
            attrs["payload"] = {"summary": summary.strip()}
        elif kind == "complete_task":
            uid = payload.get("uid")
            if set(payload) != {"uid"} or not isinstance(uid, str) or not uid.strip() or len(uid) > 255:
                raise serializers.ValidationError({"payload": "Indica el UID de la tarea"})
            attrs["payload"] = {"uid": uid.strip()}
        return attrs


class ChatMessageSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    message = serializers.CharField(max_length=2000, trim_whitespace=True, allow_blank=False)
