from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/family/", include("apps.family.urls")),
    path("api/v1/integrations/", include("apps.integrations.urls")),
    path("api/v1/calendar/", include("apps.calendar.urls")),
    path("api/v1/lists/", include("apps.lists.urls")),
    path("api/v1/home/", include("apps.home.urls")),
    path("api/v1/planning/", include("apps.planning.urls")),
    path("api/v1/jaime/", include("apps.jaime.urls")),
]
