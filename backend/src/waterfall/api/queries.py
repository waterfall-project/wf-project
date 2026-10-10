# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parameters of a query that several operations of the API share, typed once."""

from typing import Annotated

from fastapi import Query

from waterfall.api.contract.base import Text

# The parameter ``search`` of the contract, absent by default; a text, which refuses a NUL.
Search = Annotated[Text | None, Query(min_length=1, max_length=200)]
