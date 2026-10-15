from django.urls import path

from .views import ListItemDetailView, ListItemsView, ListsView


urlpatterns = [
    path("", ListsView.as_view(), name="lists"),
    path("<slug:list_id>/items/", ListItemsView.as_view(), name="list-items"),
    path("<slug:list_id>/items/<str:uid>/", ListItemDetailView.as_view(), name="list-item-detail"),
]
