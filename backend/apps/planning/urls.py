from django.urls import path

from .documents import TripDocumentDetailView, TripDocumentsView
from .menu import MenuEntriesView, MenuEntryDetailView, ShoppingPreviewView
from .recipes import RecipeDetailView, RecipesView
from .trips import (
    TripDetailView,
    TripParticipantDetailView, TripParticipantsView,
    TripPreparationDetailView, TripPreparationsView, TripsView,
)


urlpatterns = [
    path("recipes/", RecipesView.as_view(), name="recipes"),
    path("recipes/<int:pk>/", RecipeDetailView.as_view(), name="recipe-detail"),
    path("menu/", MenuEntriesView.as_view(), name="menu"),
    path("menu/<int:pk>/", MenuEntryDetailView.as_view(), name="menu-detail"),
    path("menu/shopping-preview/", ShoppingPreviewView.as_view(), name="shopping-preview"),
    path("trips/", TripsView.as_view(), name="trips"),
    path("trips/<int:pk>/", TripDetailView.as_view(), name="trip-detail"),
    path("trips/<int:trip_id>/participants/", TripParticipantsView.as_view(), name="trip-participants"),
    path("trips/<int:trip_id>/participants/<int:participant_id>/", TripParticipantDetailView.as_view(), name="trip-participant-detail"),
    path("trips/<int:trip_id>/preparations/", TripPreparationsView.as_view(), name="trip-preparations"),
    path("trips/<int:trip_id>/preparations/<int:preparation_id>/", TripPreparationDetailView.as_view(), name="trip-preparation-detail"),
    path("trips/<int:trip_id>/documents/", TripDocumentsView.as_view(), name="trip-documents"),
    path("trips/<int:trip_id>/documents/<int:document_id>/", TripDocumentDetailView.as_view(), name="trip-document-detail"),
]
