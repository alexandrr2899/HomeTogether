from django.db import transaction
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser

from .models import Recipe
from .serializers import RecipeSerializer


class RecipesView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.prefetch_related("ingredients").order_by("title", "id")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class RecipeDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.prefetch_related("ingredients")

    def perform_destroy(self, instance):
        if instance.menu_entries.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Retira la receta del menú antes de eliminarla")
        with transaction.atomic():
            instance.delete()
