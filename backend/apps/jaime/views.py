import json
import os
from datetime import timedelta
from uuid import UUID

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActionProposal
from .operations import ProposalError, confirm_proposal
from .serializers import ActionProposalSerializer, ChatMessageSerializer
from .chat_service import ChatError, run_chat
from .openclaw_client import OpenClawError, configured_client
from .bridge import execute_bridge, token_is_valid
from .models import BridgeTurn


@csrf_exempt
@require_POST
def bridge_read(request):
    if not token_is_valid(request.headers.get("Authorization", "")):
        return JsonResponse({"status": "Rechazado"}, status=403)
    if len(request.body) > 4000:
        return JsonResponse({"status": "Rechazado"}, status=400)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or set(payload) != {"turn_id", "tool", "arguments"}:
            raise ValueError
        if not isinstance(payload["turn_id"], str):
            raise ValueError
        turn_id = UUID(payload["turn_id"])
    except (ValueError, TypeError, KeyError):
        return JsonResponse({"status": "Rechazado"}, status=400)
    result, status = execute_bridge(turn_id, payload["tool"], payload["arguments"])
    return JsonResponse(result, status=status)


class ChatView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        bridge_status = "Configurado" if len(os.environ.get("HT_JAIME_BRIDGE_TOKEN", "").strip()) >= 32 else "Sin configurar"
        try:
            client = configured_client()
            if client is None:
                return Response({"status": "Sin configurar", "bridge_status": bridge_status})
            return Response({"status": "Conectado" if client.probe() else "Sin conexión", "bridge_status": bridge_status})
        except OpenClawError:
            return Response({"status": "Sin conexión", "bridge_status": bridge_status})

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        turn = None
        try:
            client = configured_client()
            if client is None:
                return Response({"status": "Sin configurar", "detail": "OpenClaw no está configurado"}, status=503)
            if len(os.environ.get("HT_JAIME_BRIDGE_TOKEN", "").strip()) >= 32:
                BridgeTurn.objects.filter(expires_at__lt=timezone.now() - timedelta(days=1)).delete()
                turn = BridgeTurn.objects.create(actor=request.user, expires_at=timezone.now() + timedelta(minutes=3))
            result = run_chat(client, request.user, serializer.validated_data["conversation_id"], serializer.validated_data["message"], bridge_turn=turn)
            if turn is not None:
                turn.refresh_from_db(fields=["proposal"])
                if turn.proposal_id:
                    result["proposal_ids"] = [str(turn.proposal_id)]
        except (OpenClawError, ChatError) as error:
            return Response({"status": "Sin conexión", "detail": str(error)}, status=503)
        finally:
            if turn is not None:
                BridgeTurn.objects.filter(pk=turn.pk).update(expires_at=timezone.now())
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
