from django.urls import path

from .views import ChatView, ProposalConfirmView, ProposalDetailView, ProposalsView, bridge_read


urlpatterns = [
    path("bridge/", bridge_read, name="jaime-bridge-read"),
    path("chat/", ChatView.as_view(), name="jaime-chat"),
    path("proposals/", ProposalsView.as_view(), name="jaime-proposals"),
    path("proposals/<uuid:proposal_id>/", ProposalDetailView.as_view(), name="jaime-proposal-detail"),
    path("proposals/<uuid:proposal_id>/confirm/", ProposalConfirmView.as_view(), name="jaime-proposal-confirm"),
]
