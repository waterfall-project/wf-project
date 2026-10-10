# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The authors of the rows as the contract names them, and the caller as the journal names it."""

from waterfall.api.contract.models import ActorRef
from waterfall.core.users.interface import Account, Author, display_name
from waterfall.platform.audit import AuditActor


def actor_ref(author: Author | None) -> ActorRef:
    """Name the author of a row: an account by its name, or the platform (WF-DAT-0070)."""
    if author is None:
        return ActorRef.model_validate({"kind": "platform"})
    return ActorRef.model_validate(
        {"kind": "user", "user_id": author.user_id, "display_name": author.display_name}
    )


def audit_actor(account: Account) -> AuditActor:
    """Name the caller as the journal of audit keeps it: as it is shown at that moment."""
    return AuditActor(account.user_id, display_name(account.first_name, account.last_name))
