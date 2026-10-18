# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The authors of the rows as the contract names them."""

from waterfall.api.contract.models import ActorRef
from waterfall.core.users.interface import Author


def actor_ref(author: Author | None) -> ActorRef:
    """Name the author of a row: an account by its name, or the platform (WF-DAT-0070)."""
    if author is None:
        return ActorRef.model_validate({"kind": "platform"})
    return ActorRef.model_validate(
        {"kind": "user", "user_id": author.user_id, "display_name": author.display_name}
    )
