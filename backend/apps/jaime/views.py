from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActionProposal
from .operations import ProposalError, confirm_proposal
from .serializers import ActionProposalSerializer, ChatMessageSerializer
from .chat_service import ChatError, run_chat
from .openclaw_client import OpenClawError, configured_client


class ChatView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            client = configured_client()
            if client is None:
                return Response({"status": "Sin configurar"})
            return Response({"status": "Conectado" if client.probe() else "Sin conexión"})
        except OpenClawError:
            return Response({"status": "Sin conexión"})

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            client = configured_client()
            if client is None:
                return Response({"status": "Sin configurar", "detail": "OpenClaw no está configurado"}, status=503)
            result = run_chat(client, request.user, serializer.validated_data["conversation_id"], serializer.validated_data["message"])
        except (OpenClawError, ChatError) as error:
            return Response({"status": "Sin conexión", "detail": str(error)}, status=503)
        return Response(result)


class ProposalsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        proposals = ActionProposal.objects.filter(actor=request.user).order_by("-created_at")[:50]
        return Response(ActionProposalSerializer(proposals, many=True).data)

    def post(self, request):
        serializer = ActionProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proposal = serializer.save(actor=request.user)
        return Response(ActionProposalSerializer(proposal).data, status=201)


class ProposalDetailView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, proposal_id):
        proposal = get_object_or_404(ActionProposal, pk=proposal_id, actor=request.user)
        if proposal.state != "pending":
            return Response({"detail": "Solo se puede descartar una propuesta pendiente"}, status=409)
        proposal.delete()
        return Response(status=204)


class ProposalConfirmView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, proposal_id):
        try:
            proposal = confirm_proposal(proposal_id, request.user)
        except ProposalError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        return Response(ActionProposalSerializer(proposal).data)
