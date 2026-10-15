"""Import the small domain models so Django registers them for migrations."""

from .recipe_models import Ingredient, Recipe
from .menu_models import MenuEntry
from .trip_models import Trip, TripDocument, TripParticipant, TripPreparation

__all__ = (
    "Recipe", "Ingredient", "MenuEntry", "Trip", "TripParticipant", "TripPreparation", "TripDocument",
)
