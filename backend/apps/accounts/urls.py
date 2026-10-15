from django.urls import path

from .views import MeView, csrf_cookie, login_view, logout_view


urlpatterns = [
    path("csrf/", csrf_cookie, name="csrf-cookie"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
