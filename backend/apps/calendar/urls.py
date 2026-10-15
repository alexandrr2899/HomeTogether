from django.urls import path

from .views import (CalendarEventDetailView, CalendarEventsView, CalendarOptionsView, CalendarSelectView,
                    OAuthCallbackView, OAuthResultView, OAuthStartView)


urlpatterns = [
    path("events/", CalendarEventsView.as_view(), name="calendar-events"),
    path("events/<str:event_id>/", CalendarEventDetailView.as_view(), name="calendar-event-detail"),
    path("options/", CalendarOptionsView.as_view(), name="calendar-options"),
    path("select/", CalendarSelectView.as_view(), name="calendar-select"),
    path("oauth/start/", OAuthStartView.as_view(), name="google-oauth-start"),
    path("oauth/callback/", OAuthCallbackView.as_view(), name="google-oauth-callback"),
    path("oauth/result/", OAuthResultView.as_view(), name="google-oauth-result"),
]
