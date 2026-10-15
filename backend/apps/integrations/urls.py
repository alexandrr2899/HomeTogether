from django.urls import path

from .views import ConnectionsView


urlpatterns = [path("connections/", ConnectionsView.as_view(), name="connections")]
