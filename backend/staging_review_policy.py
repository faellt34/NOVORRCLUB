"""Permissões de pré-visualização na homologação RRClub.

Isolado do backend operacional. Não concede permissões de escrita nem Stripe.
Uma identidade real deve ser autenticada pelo Google no servidor antes de chamar
estas funções. Os grants devem vir da base de dados, nunca do cliente.
"""
from dataclasses import dataclass
from typing import FrozenSet

REVIEW_ROLES = frozenset({"admin", "partner", "influencer"})
VIEW_ONLY_ACTIONS = frozenset({"dashboard.read", "report.read", "campaign.read", "qr.preview"})


@dataclass(frozen=True)
class ReviewerIdentity:
    subject: str
    authenticated: bool
    account_active: bool
    actual_role: str
    allowed_views: FrozenSet[str]
    reviewer_grant_active: bool


def can_view_dashboard(identity: ReviewerIdentity, requested_role: str) -> bool:
    """Fail-closed: only an active admin with an explicit grant may switch views."""
    return (
        bool(identity.subject)
        and identity.authenticated is True
        and identity.account_active is True
        and identity.actual_role == "admin"
        and identity.reviewer_grant_active is True
        and requested_role in REVIEW_ROLES
        and requested_role in identity.allowed_views
    )


def can_perform_preview_action(
    identity: ReviewerIdentity, requested_role: str, action: str
) -> bool:
    """Switching views never authorizes mutations, Stripe or payouts."""
    return can_view_dashboard(identity, requested_role) and action in VIEW_ONLY_ACTIONS
