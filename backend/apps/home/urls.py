from django.urls import path

from .views import MyWellnessView, PresenceView, SharedWellnessView, WellnessCatalogView, WellnessPreferencesView


urlpatterns = [
    path("presence/", PresenceView.as_view(), name="presence"),
    path("wellness/me/", MyWellnessView.as_view(), name="wellness-me"),
    path("wellness/catalog/", WellnessCatalogView.as_view(), name="wellness-catalog"),
    path("wellness/shared/", SharedWellnessView.as_view(), name="wellness-shared"),
    path("wellness/preferences/", WellnessPreferencesView.as_view(), name="wellness-preferences"),
]
