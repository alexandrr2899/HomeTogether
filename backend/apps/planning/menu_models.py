from django.db import models

from .recipe_models import Recipe


class MenuEntry(models.Model):
    MEALS = (("desayuno", "Desayuno"), ("almuerzo", "Almuerzo"), ("cena", "Cena"), ("otro", "Otro"))
    date = models.DateField()
    meal = models.CharField(max_length=12, choices=MEALS)
    recipe = models.ForeignKey(Recipe, related_name="menu_entries", on_delete=models.PROTECT)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("date", "meal", "id")
        constraints = [models.UniqueConstraint(fields=("date", "meal", "recipe"), name="unique_recipe_meal_on_date")]
