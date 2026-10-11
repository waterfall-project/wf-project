# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The avatars: the caller puts, replaces and withdraws its own; any caller reads any one.

An avatar is the holder's alone (WF-ADM-0080): the family ``me`` changes the caller's, and no
operation changes the avatar of another. It is kept in the base with the account (§4.4.1), within
the bound of the installation (``avatar_max_bytes``). An image is a PNG or a JPEG by its content,
not by the type its request says: it is kept with the type its content shows, and served with it.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from waterfall.api.authentication import Caller, ServicesOf, Transaction, caller
from waterfall.core.users.interface import (
    Avatar,
    image_type,
    put_avatar,
    read_avatar,
    remove_avatar,
)
from waterfall.platform.errors import (
    BadRequestError,
    FieldError,
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
)
from waterfall.platform.installation import read_settings

router = APIRouter()

MALFORMED_REQUEST = "MALFORMED_REQUEST"
FILE_TOO_LARGE = "FILE_TOO_LARGE"
VALIDATION_FAILED = "VALIDATION_FAILED"
NOT_FOUND = "NOT_FOUND"
# The types of image the contract lets a request say it sends.
SENT_TYPES = frozenset({"image/png", "image/jpeg"})


def avatar_bound(services: ServicesOf) -> int:
    """Read the size an avatar may have, in bytes: a setting of the installation."""
    with services.database.transaction() as session:
        return read_settings(session).avatar_max_bytes


async def received_avatar(request: Request, bound: Annotated[int, Depends(avatar_bound)]) -> Avatar:
    """Read the image a request carries, within the bound of the installation.

    A request that says no type of image the contract declares, or that carries nothing, cannot
    be read (400). One beyond the bound is refused as soon as it says so or as its bytes pass it,
    without being read further (413). An image whose content is neither a PNG nor a JPEG is
    refused (422), whatever type its request says.
    """
    sent_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
    if sent_type not in SENT_TYPES:
        raise BadRequestError(MALFORMED_REQUEST)
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > bound:
        raise PayloadTooLargeError(FILE_TOO_LARGE)
    image = bytearray()
    async for chunk in request.stream():
        image += chunk
        if len(image) > bound:
            raise PayloadTooLargeError(FILE_TOO_LARGE)
    if not image:
        raise BadRequestError(MALFORMED_REQUEST)
    media_type = image_type(bytes(image))
    if media_type is None:
        raise UnprocessableError(VALIDATION_FAILED, fields=(FieldError("", VALIDATION_FAILED),))
    return Avatar(bytes(image), media_type)


@router.put("/me/avatar", operation_id="putMyAvatar", status_code=204, tags=["me"])
def put_my_avatar(
    account: Caller, avatar: Annotated[Avatar, Depends(received_avatar)], session: Transaction
) -> Response:
    """Put an avatar on the caller's account, or replace the one it had (WF-ADM-0080).

    The caller is known before its image is read: a request without a session reads nothing.
    """
    put_avatar(session, account.user_id, avatar)
    return Response(status_code=204)


@router.delete("/me/avatar", operation_id="deleteMyAvatar", status_code=204, tags=["me"])
def delete_my_avatar(account: Caller, session: Transaction) -> Response:
    """Withdraw the caller's avatar: its account shows its image by default (WF-ADM-0080)."""
    remove_avatar(session, account.user_id)
    return Response(status_code=204)


@router.get(
    "/users/{user_id}/avatar",
    operation_id="getUserAvatar",
    tags=["users"],
    dependencies=[Depends(caller)],
)
def get_user_avatar(user_id: UUID, session: Transaction) -> Response:
    """Give the avatar of an account, as its holder put it, to any caller (WF-ADM-0080).

    It is shown wherever the account is cited, to whoever reads the citation: no permission is
    asked for. An account without one, like an account that does not exist, has none (404).
    """
    avatar = read_avatar(session, user_id)
    if avatar is None:
        raise NotFoundError(NOT_FOUND)
    return Response(content=avatar.image, media_type=avatar.media_type)
