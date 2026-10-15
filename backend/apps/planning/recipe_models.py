from django.conf import settings
from django.db import models


class Recipe(models.Model):
    title = models.CharField(max_length=180)
    instructions = models.TextField(blank=True)
    servings = models.PositiveSmallIntegerField(default=2)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Ingredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="ingredients", on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    amount = models.CharField(max_length=80, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("position", "id")
