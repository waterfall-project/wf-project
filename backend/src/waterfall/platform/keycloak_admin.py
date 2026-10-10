# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The administration API of Keycloak, reached as the service account of the realm (PBS-2.5).

Through it the service reads where an account comes from and closes its sessions (WF-ADM-0070,
WF-SEC-0020). The token of the service account is kept until shortly before it expires.

Only Keycloak itself answers this API: what is here is tried against the Keycloak of the service
platform, whose tests measure it (``make test-keycloak``); the measure of the back, which runs no
Keycloak, leaves this module out by its path.
"""

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx2

from waterfall.platform.keycloak import Keycloak, expect
from waterfall.platform.settings import ServiceSettings

SERVICE_CLIENT = "waterfall-service"
# The token of the service account is renewed this long before it expires.
TOKEN_MARGIN_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class ProviderAccount:
    """An account of the realm, as its administration API describes it.

    A name or an address the realm does not hold is an empty text.
    """

    subject: str
    last_name: str
    first_name: str
    email: str
    # Read from a directory the realm federates: the account has a federation link.
    is_federated: bool
    # Linked to an external provider the realm relays to: the account has a federated identity.
    is_relayed: bool


def _text(document: Mapping[str, Any], name: str) -> str:
    value = document.get(name)
    return value if isinstance(value, str) else ""


class KeycloakAdmin:
    """The administration API of the realm, reached through the client of Keycloak."""

    def __init__(
        self,
        keycloak: Keycloak,
        settings: ServiceSettings,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Prepare the client; no token is asked for before a request needs one."""
        self._keycloak = keycloak
        self._admin = f"/admin/realms/{quote(settings.keycloak_realm, safe='')}"
        self._secret = settings.service_client_secret
        self._clock = clock
        self._token: tuple[str, float] | None = None
        self._token_lock = threading.Lock()

    def read_account(self, subject: str) -> ProviderAccount | None:
        """Read an account of the realm and where it comes from, or ``None`` if it has none."""
        user = f"{self._admin}/users/{quote(subject, safe='')}"
        response = self._as_service("GET", user)
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        found = cast("Mapping[str, Any]", expect(response, HTTPStatus.OK).json())
        is_federated = bool(found.get("federationLink"))
        is_relayed = False
        if not is_federated:
            identities = expect(
                self._as_service("GET", f"{user}/federated-identity"), HTTPStatus.OK
            ).json()
            is_relayed = bool(identities)
        return ProviderAccount(
            subject=subject,
            last_name=_text(found, "lastName"),
            first_name=_text(found, "firstName"),
            email=_text(found, "email"),
            is_federated=is_federated,
            is_relayed=is_relayed,
        )

    def close_sessions(self, subject: str) -> None:
        """Close every session of an account, on every device (WF-SEC-0020).

        An account the realm no longer holds has no session left to close.
        """
        response = self._as_service("POST", f"{self._admin}/users/{quote(subject, safe='')}/logout")
        if response.status_code != HTTPStatus.NOT_FOUND:
            expect(response, HTTPStatus.NO_CONTENT)

    def _service_token(self, *, renew: bool = False) -> str:
        with self._token_lock:
            if self._token is not None and not renew and self._clock() < self._token[1]:
                return self._token[0]
            asked_at = self._clock()
            response = self._keycloak.send(
                "POST",
                f"{self._keycloak.protocol}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": SERVICE_CLIENT,
                    "client_secret": self._secret.get_secret_value(),
                },
            )
            granted = cast("Mapping[str, Any]", expect(response, HTTPStatus.OK).json())
            token = cast("str", granted["access_token"])
            lifetime = float(granted["expires_in"])
            self._token = (token, asked_at + lifetime - TOKEN_MARGIN_SECONDS)
            return token

    def _as_service(self, method: str, path: str) -> httpx2.Response:
        """Send a request of the administration API as the service account.

        A token refused before its time — the realm restarted, its keys rotated, the sessions
        of the service account closed — is renewed once.
        """
        response = self._send(method, path, self._service_token())
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            response = self._send(method, path, self._service_token(renew=True))
        return response

    def _send(self, method: str, path: str, token: str) -> httpx2.Response:
        return self._keycloak.send(method, path, headers={"Authorization": f"Bearer {token}"})
