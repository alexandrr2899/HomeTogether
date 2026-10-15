from django.urls import path

from .views import ChatView, ProposalConfirmView, ProposalDetailView, ProposalsView


urlpatterns = [
    path("chat/", ChatView.as_view(), name="jaime-chat"),
    path("proposals/", ProposalsView.as_view(), name="jaime-proposals"),
    path("proposals/<uuid:proposal_id>/", ProposalDetailView.as_view(), name="jaime-proposal-detail"),
    path("proposals/<uuid:proposal_id>/confirm/", ProposalConfirmView.as_view(), name="jaime-proposal-confirm"),
]
