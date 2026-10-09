# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The correlation identifier that follows a request into its logs and its errors (WF-OBS-0020)."""

import re
import uuid

HEADER = "X-Correlation-ID"

# Where the identifier of a request is kept in its ASGI scope.
SCOPE_KEY = "correlation_id"

# The form `Problem.correlation_id` has in the contract.
FORM = re.compile(r"[A-Za-z0-9._-]{1,64}")


def correlation_id_from(received: str | None) -> str:
    """Take the identifier a caller sent if it has the form of the contract, else make one."""
    if received is not None and FORM.fullmatch(received):
        return received
    return str(uuid.uuid4())
