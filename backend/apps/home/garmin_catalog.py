"""A bounded, reviewed catalog of Garmin scalar states; no sensor attributes are exposed."""

from dataclasses import dataclass

from apps.integrations.models import ExternalEntityLink


@dataclass(frozen=True)
class GarminStat:
    suffix: str
    label: str
    group: str
    kind: str
    unit: str | None = None


GARMIN_STATS = {
    "steps": GarminStat("steps", "Pasos de hoy", "Actividad diaria", "number", "steps"),
    "sleep": GarminStat("sleep_duration", "Tiempo dormido", "Sueño", "duration", "min"),
    "activity": GarminStat("last_activity", "Última actividad", "Actividad diaria", "text"),
    "distance": GarminStat("distance", "Distancia de hoy", "Actividad diaria", "number", "m"),
    "floors": GarminStat("floors_ascended", "Pisos subidos", "Actividad diaria", "number", "floors"),
    "active_calories": GarminStat("active_calories", "Calorías activas", "Actividad diaria", "number", "kcal"),
    "intensity_minutes": GarminStat("intensity_minutes", "Minutos de intensidad", "Actividad diaria", "duration", "min"),
    "sleep_score": GarminStat("sleep_score", "Puntuación de sueño", "Sueño", "number"),
    "deep_sleep": GarminStat("deep_sleep", "Sueño profundo", "Sueño", "duration", "min"),
    "rem_sleep": GarminStat("rem_sleep", "Sueño REM", "Sueño", "duration", "min"),
    "body_battery": GarminStat("body_battery", "Batería corporal", "Salud y recuperación", "number", "%"),
    "resting_heart_rate": GarminStat("resting_heart_rate", "Pulso en reposo", "Salud y recuperación", "number", "bpm"),
    "average_stress": GarminStat("average_stress_level", "Estrés promedio", "Salud y recuperación", "number", "level"),
    "hrv_status": GarminStat("hrv_status", "Estado de HRV", "Salud y recuperación", "text"),
    "hrv_night": GarminStat("hrv_last_night_average", "HRV de la última noche", "Salud y recuperación", "number", "ms"),
    "training_readiness": GarminStat("training_readiness", "Preparación para entrenar", "Entrenamiento", "number", "%"),
    "vo2_max": GarminStat("vo2_max", "VO₂ máximo", "Entrenamiento", "number", "mL/(kg·min)"),
    "weight": GarminStat("weight", "Peso", "Salud y recuperación", "number", "kg"),
}

DEFAULT_VISIBLE_STATS = ["steps", "sleep", "activity"]


def default_visible_stats():
    return DEFAULT_VISIBLE_STATS.copy()


def garmin_prefix(account):
    link = ExternalEntityLink.objects.filter(
        account=account, provider="home_assistant", purpose="wellness_steps",
    ).first()
    if not link or not link.entity_id.startswith("sensor.") or not link.entity_id.endswith("_steps"):
        return None
    return link.entity_id.removesuffix("steps")


def entity_id_for(prefix, key):
    return f"{prefix}{GARMIN_STATS[key].suffix}"
