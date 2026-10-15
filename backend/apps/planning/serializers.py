from django.db import transaction
from rest_framework import serializers

from .models import Ingredient, MenuEntry, Recipe, Trip, TripDocument, TripParticipant, TripPreparation


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "amount", "position")
        read_only_fields = ("id",)


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True)

    class Meta:
        model = Recipe
        fields = ("id", "title", "instructions", "servings", "ingredients", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients", [])
        recipe = Recipe.objects.create(**validated_data)
        Ingredient.objects.bulk_create(Ingredient(recipe=recipe, **ingredient) for ingredient in ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if ingredients is not None:
            instance.ingredients.all().delete()
            Ingredient.objects.bulk_create(Ingredient(recipe=instance, **ingredient) for ingredient in ingredients)
        return instance


class MenuEntrySerializer(serializers.ModelSerializer):
    recipe_title = serializers.CharField(source="recipe.title", read_only=True)

    class Meta:
        model = MenuEntry
        fields = ("id", "date", "meal", "recipe", "recipe_title", "notes")


class TripParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripParticipant
        fields = ("id", "profile", "name")


class TripPreparationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripPreparation
        fields = ("id", "title", "done")


class TripDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripDocument
        fields = ("id", "original_name", "size", "uploaded_at")


class TripSerializer(serializers.ModelSerializer):
    participants = TripParticipantSerializer(many=True, read_only=True)
    preparations = TripPreparationSerializer(many=True, read_only=True)
    documents = TripDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Trip
        fields = (
            "id", "title", "destination", "start_date", "end_date", "notes",
            "participants", "preparations", "documents", "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        start = attrs.get("start_date", instance.start_date if instance else None)
        end = attrs.get("end_date", instance.end_date if instance else None)
        if start and end and end < start:
            raise serializers.ValidationError("La fecha final debe ser posterior al inicio")
        return attrs
