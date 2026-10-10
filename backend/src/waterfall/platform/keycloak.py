# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The client of Keycloak: the keys of the realm and its administration API (PBS-2.5).

An access token is validated by the public keys of the realm — signature, issuer, audience,
expiry — and gives nothing but its subject (WF-ARC-0030). The keys are kept, and read again
when a token names a key that is not among them: the realm has rotated its keys. The
administration API is reached as the service account of the realm, whose token is kept until
shortly before it expires; through it the service reads where an account comes from and closes
its sessions (WF-ADM-0070, WF-SEC-0020).

Keycloak is reached on its back channel, the issuer of the tokens being the address the browser
knows it by. A Keycloak that does not answer is a component unavailable (503); an answer that
breaks what the realm promises is a defect of the platform, raised as such.
"""

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx2
import jwt
from jwt import PyJWK, PyJWKSet

from waterfall.platform.errors import UnauthenticatedError, UnavailableError
from waterfall.platform.logs import get_logger
from waterfall.platform.settings import ServiceSettings

# The audience of the tokens the API accepts: a token lent to another client is not for it.
AUDIENCE = "waterfall-api"
SERVICE_CLIENT = "waterfall-service"
# The algorithm the keys of the realm sign with; a token that says another one is refused.
ALGORITHMS = ("RS256",)
TIMEOUT_SECONDS = 10.0
# A token naming a key that is not known makes the keys read again, but not more often than
# this: a token naming a key the realm never had would otherwise send every request to Keycloak.
# A key the realm has just added is thus taken within this delay at worst.
KEYS_REREAD_SECONDS = 10.0
# The token of the service account is renewed this long before it expires.
TOKEN_MARGIN_SECONDS = 30.0

SESSION_REQUIRED = "SESSION_REQUIRED"
SESSION_EXPIRED = "SESSION_EXPIRED"
COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
COMPONENT = "identity_provider"

logger = get_logger(__name__)


class IdentityProviderError(RuntimeError):
    """Keycloak answered something the realm of Waterfall does not allow: a defect to correct."""


def unavailable() -> UnavailableError:
    """Refuse an operation that needs Keycloak while it does not answer (WF-EXP-0040)."""
    return UnavailableError(COMPONENT_UNAVAILABLE, {"component": COMPONENT})


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


class Keycloak:
    """The realm of Waterfall, as the API and the worker reach it."""

    def __init__(
        self, settings: ServiceSettings, clock: Callable[[], float] = time.monotonic
    ) -> None:
        """Prepare the client; nothing is asked of Keycloak before a token is to be validated."""
        realm = quote(settings.keycloak_realm, safe="")
        self.issuer = f"{settings.keycloak_address.rstrip('/')}/realms/{realm}"
        backchannel = (settings.keycloak_backchannel or settings.keycloak_address).rstrip("/")
        self._http = httpx2.Client(base_url=backchannel, timeout=TIMEOUT_SECONDS)
        self._protocol = f"/realms/{realm}/protocol/openid-connect"
        self._admin = f"/admin/realms/{realm}"
        self._secret = settings.service_client_secret
        self._clock = clock
        self._keys: Mapping[str, PyJWK] = {}
        self._keys_read_at: float | None = None
        self._keys_lock = threading.Lock()
        self._token: tuple[str, float] | None = None
        self._token_lock = threading.Lock()

    def close(self) -> None:
        """Close the connections to Keycloak."""
        self._http.close()

    def subject_of(self, token: str) -> str:
        """Validate an access token and give its subject, or refuse it (401).

        An expired token is ``SESSION_EXPIRED``; any other fault — a key the realm does not
        have, a signature that does not match, another issuer, another audience — is
        ``SESSION_REQUIRED``. The signature is checked first: an expired token signed by another
        key is not merely expired.
        """
        try:
            key_id = jwt.get_unverified_header(token).get("kid")
        except jwt.PyJWTError:
            raise UnauthenticatedError(SESSION_REQUIRED) from None
        key = self._key(key_id) if isinstance(key_id, str) else None
        if key is None:
            raise UnauthenticatedError(SESSION_REQUIRED)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=AUDIENCE,
                issuer=self.issuer,
                # The moment of issue is not checked: a clock of Keycloak a second ahead of that
                # of the API would refuse every new token. The expiry bounds the token.
                options={"require": ["exp", "iss", "aud", "sub"], "verify_iat": False},
            )
        except jwt.ExpiredSignatureError:
            raise UnauthenticatedError(SESSION_EXPIRED) from None
        except jwt.PyJWTError:
            raise UnauthenticatedError(SESSION_REQUIRED) from None
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject:
            raise UnauthenticatedError(SESSION_REQUIRED)
        return subject

    def read_account(self, subject: str) -> ProviderAccount | None:
        """Read an account of the realm and where it comes from, or ``None`` if it has none."""
        user = f"{self._admin}/users/{quote(subject, safe='')}"
        response = self._as_service("GET", user)
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        found = cast("Mapping[str, Any]", self._expect(response, HTTPStatus.OK).json())
        is_federated = bool(found.get("federationLink"))
        is_relayed = False
        if not is_federated:
            identities = self._expect(
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
            self._expect(response, HTTPStatus.NO_CONTENT)

    def _key(self, key_id: str) -> PyJWK | None:
        key = self._keys.get(key_id)
        if key is not None:
            return key
        with self._keys_lock:
            # Another request may have read them while this one waited.
            key = self._keys.get(key_id)
            read_at = self._keys_read_at
            if key is None and (read_at is None or self._clock() - read_at >= KEYS_REREAD_SECONDS):
                self._keys = self._read_keys()
                self._keys_read_at = self._clock()
                key = self._keys.get(key_id)
            return key

    def _read_keys(self) -> Mapping[str, PyJWK]:
        response = self._expect(self._send("GET", f"{self._protocol}/certs"), HTTPStatus.OK)
        try:
            keys = PyJWKSet.from_dict(cast("dict[str, Any]", response.json())).keys
        except (jwt.PyJWTError, AttributeError, ValueError) as error:
            message = "the keys of the realm are not usable"
            raise IdentityProviderError(message) from error
        return {key.key_id: key for key in keys if key.key_id and key.public_key_use != "enc"}

    def _service_token(self, *, renew: bool = False) -> str:
        with self._token_lock:
            if self._token is not None and not renew and self._clock() < self._token[1]:
                return self._token[0]
            asked_at = self._clock()
            response = self._send(
                "POST",
                f"{self._protocol}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": SERVICE_CLIENT,
                    "client_secret": self._secret.get_secret_value(),
                },
            )
            granted = cast("Mapping[str, Any]", self._expect(response, HTTPStatus.OK).json())
            token = cast("str", granted["access_token"])
            lifetime = float(granted["expires_in"])
            self._token = (token, asked_at + lifetime - TOKEN_MARGIN_SECONDS)
            return token

    def _as_service(self, method: str, path: str) -> httpx2.Response:
        """Send a request of the administration API as the service account.

        A token refused before its time — the realm restarted, its keys rotated — is renewed
        once.
        """
        response = self._send(method, path, headers=self._bearer(self._service_token()))
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            renewed = self._service_token(renew=True)
            response = self._send(method, path, headers=self._bearer(renewed))
        return response

    @staticmethod
    def _bearer(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _send(self, method: str, path: str, **options: Any) -> httpx2.Response:
        try:
            response = self._http.request(method, path, **options)
        except httpx2.HTTPError as error:
            logger.warning("identity_provider.unreachable", fault=type(error).__name__)
            raise unavailable() from None
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            logger.warning("identity_provider.failed", status=response.status_code)
            raise unavailable()
        return response

    @staticmethod
    def _expect(response: httpx2.Response, status: int) -> httpx2.Response:
        if response.status_code != status:
            request = response.request
            message = f"{request.method} {request.url.path} answered {response.status_code}"
            raise IdentityProviderError(message)
        return response
