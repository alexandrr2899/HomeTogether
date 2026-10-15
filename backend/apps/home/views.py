from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from .models import WellnessPreference
from .garmin_catalog import GARMIN_STATS
from .wellness import available_garmin_stats, preferences_for, read_wellness

from .presence import read_presence


class PresenceView(APIView):
    def get(self, request):
        return Response(read_presence())


class WellnessPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellnessPreference
        fields = ("visible_metrics", "shared_metrics", "allow_jaime")

    def validate(self, attrs):
        visible = attrs.get("visible_metrics", self.instance.visible_metrics if self.instance else [])
        shared = attrs.get("shared_metrics", self.instance.shared_metrics if self.instance else [])
        for label, values in (("visible_metrics", visible), ("shared_metrics", shared)):
            if (not isinstance(values, list) or len(values) > len(GARMIN_STATS) or
                    any(not isinstance(key, str) or key not in GARMIN_STATS for key in values) or
                    len(set(values)) != len(values)):
                raise serializers.ValidationError({label: "Selecciona indicadores válidos sin repetir"})
        if not set(shared).issubset(visible):
            raise serializers.ValidationError({"shared_metrics": "Solo puedes compartir indicadores que muestras"})
        return attrs


class MyWellnessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(read_wellness(request.user, request.user))


class WellnessCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(available_garmin_stats(request.user))


class WellnessPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(WellnessPreferencesSerializer(preferences_for(request.user)).data)

    def patch(self, request):
        preference = preferences_for(request.user)
        serializer = WellnessPreferencesSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SharedWellnessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        from apps.integrations.models import ExternalEntityLink
        accounts = get_user_model().objects.filter(pk__in=ExternalEntityLink.objects.filter(
            provider="home_assistant", purpose__in=("wellness_steps", "wellness_sleep", "wellness_activity"),
        ).values("account_id")).exclude(pk=request.user.pk)
        return Response([{"name": account.first_name or account.get_username(), **read_wellness(account, request.user)}
                         for account in accounts if preferences_for(account).shared_metrics])
