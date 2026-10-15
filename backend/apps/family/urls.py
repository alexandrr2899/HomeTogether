from django.urls import path

from .dates import ImportantDateDetailView, ImportantDatesView
from .documents import PrivateDocumentDetailView, PrivateDocumentsView
from .profiles import FamilyProfileDetailView, FamilyProfilesView
from .responsibilities import ResponsibilityDetailView, ResponsibilitySourceView, ResponsibilitiesView
from .views import FamilyStatusView


urlpatterns = [
    path("status/", FamilyStatusView.as_view(), name="family-status"),
    path("profiles/", FamilyProfilesView.as_view(), name="family-profiles"),
    path("profiles/<int:pk>/", FamilyProfileDetailView.as_view(), name="family-profile-detail"),
    path("profiles/<int:profile_id>/dates/", ImportantDatesView.as_view(), name="family-dates"),
    path("profiles/<int:profile_id>/dates/<int:date_id>/", ImportantDateDetailView.as_view(), name="family-date-detail"),
    path("profiles/<int:profile_id>/responsibilities/", ResponsibilitiesView.as_view(), name="family-responsibilities"),
    path("profiles/<int:profile_id>/responsibilities/<int:responsibility_id>/", ResponsibilityDetailView.as_view(), name="family-responsibility-detail"),
    path("profiles/<int:profile_id>/responsibilities/<int:responsibility_id>/source/", ResponsibilitySourceView.as_view(), name="family-responsibility-source"),
    path("profiles/<int:profile_id>/documents/", PrivateDocumentsView.as_view(), name="family-documents"),
    path("profiles/<int:profile_id>/documents/<int:document_id>/", PrivateDocumentDetailView.as_view(), name="family-document-detail"),
]
