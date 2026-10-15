from django.contrib import admin

from .models import ExternalEntityLink


@admin.register(ExternalEntityLink)
class ExternalEntityLinkAdmin(admin.ModelAdmin):
    list_display = ("account", "provider", "purpose", "entity_id")
    list_filter = ("provider", "purpose")
    search_fields = ("account__username", "entity_id")
