# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The typed exceptions a refusal is raised with: a code, its parameters, never a sentence.

The core raises them, and only the API turns them into the error envelope of the contract
(WF-ARC-0110). The status follows the contract: 404 when reading is forbidden, 403 when it
is writing or the quality of contributor, 409 for a conflict of state, 412 for a stale
``lock_version``. The code is a member of ``ErrorCode`` in the contract; the envelope refuses
one that is not.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldError:
    """The refusal of one field: where it is, why, and what the reason needs to say."""

    pointer: str
    code: str
    params: Mapping[str, Any] = field(default_factory=dict[str, Any])


class ServiceError(Exception):
    """A refusal of the service, carrying the code and the parameters the front renders."""

    status: int = 400

    def __init__(
        self,
        code: str,
        params: Mapping[str, Any] | None = None,
        fields: tuple[FieldError, ...] = (),
    ) -> None:
        super().__init__(code)
        self.code = code
        self.params: Mapping[str, Any] = params or {}
        self.fields = fields


class BadRequestError(ServiceError):
    """The request cannot be read (400)."""

    status = 400


class UnauthenticatedError(ServiceError):
    """No valid token, or a deactivated account (401)."""

    status = 401


class ForbiddenError(ServiceError):
    """The permission is there, a condition is missing (403)."""

    status = 403


class NotFoundError(ServiceError):
    """The object does not exist, or may not be read (404)."""

    status = 404


class ConflictError(ServiceError):
    """The state forbids the operation, or a unique value is taken (409)."""

    status = 409


class PreconditionFailedError(ServiceError):
    """The ``lock_version`` is stale (412)."""

    status = 412


class UnprocessableError(ServiceError):
    """A rule refuses the entity; ``fields`` locates each refusal (422)."""

    status = 422


class UnavailableError(ServiceError):
    """A component the instance needs does not answer (503)."""

    status = 503
