# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Identifiers of the rows: UUID version 7, drawn by the service and never by the database.

A version 7 identifier starts with the time it was drawn at, so the rows sort in the order they
were created; it is random for the rest, so two instances of the service drawing at the same
instant do not produce the same one (WF-DAT-0060). Python 3.13 has no ``uuid.uuid7`` yet.
"""

from uuid import UUID

import uuid_utils


def new_id() -> UUID:
    """Draw a new identifier."""
    return UUID(bytes=uuid_utils.uuid7().bytes)
