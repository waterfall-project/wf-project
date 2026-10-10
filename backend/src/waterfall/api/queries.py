# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parameters of a query that several operations of the API share, typed once."""

from typing import Annotated

from fastapi import Query

# The parameter ``search`` of the contract, absent by default. PostgreSQL refuses a text that
# holds a NUL: refused here, it is a value the field refuses (422), not a failure of the database.
Search = Annotated[str | None, Query(min_length=1, max_length=200, pattern=r"^[^\x00]*$")]
