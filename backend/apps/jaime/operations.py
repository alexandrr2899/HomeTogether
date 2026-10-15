from django.db import transaction
from django.utils import timezone

from apps.lists.operations import ListOperationError, create_item, update_item

from .models import ActionProposal


class ProposalError(Exception):
    def __init__(self, detail, status_code=409):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def confirm_proposal(proposal_id, actor):
    with transaction.atomic():
        proposal = ActionProposal.objects.select_for_update().filter(pk=proposal_id, actor=actor).first()
        if proposal is None:
            raise ProposalError("Propuesta no disponible", 404)
        if proposal.state != "pending":
            raise ProposalError("Esta propuesta ya se confirmó o requiere revisión")
        try:
            if proposal.kind == "add_task":
                item = create_item("tareas", proposal.id, proposal.payload["summary"], actor)
            elif proposal.kind == "add_shopping":
                item = create_item("compras", proposal.id, proposal.payload["summary"], actor)
            elif proposal.kind == "complete_task":
                item = update_item("tareas", proposal.payload["uid"], {"status": "completed"})
            else:
                raise ProposalError("Acción no permitida", 400)
        except ListOperationError as error:
            proposal.state = "uncertain"
            proposal.error = error.detail[:255]
            proposal.save(update_fields=("state", "error"))
            # Commit the uncertain state so another request cannot repeat an external write.
            result = (None, error)
        else:
            proposal.state = "confirmed"
            proposal.result = {"source": "home_assistant", "list_id": "compras" if proposal.kind == "add_shopping" else "tareas", "uid": item.get("uid", ""), "summary": item.get("summary", ""), "status": item.get("status", "")}
            proposal.confirmed_at = timezone.now()
            proposal.save(update_fields=("state", "result", "confirmed_at"))
            result = (proposal, None)
    if result[1] is not None:
        raise ProposalError(f"{result[1].detail}. Revisa la lista antes de crear otra propuesta.", result[1].status_code)
    return result[0]
