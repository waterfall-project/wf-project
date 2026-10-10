# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The client of Keycloak: the keys of the realm, and how Keycloak is reached (PBS-2.5).

An access token is validated by the public keys of the realm — signature, issuer, audience,
expiry — and gives nothing but its subject (WF-ARC-0030). The keys are kept, read again when a
token names a key that is not among them — the realm has added one — and when they have been
kept for the life of an access token: a key the realm has removed stops serving within it. While
Keycloak fails to give them, the keys held serve, and a request whose key is held does not wait
for those being read; a token whose key is not held is refused as Keycloak's failure, never as a
session missing. The administration API is ``keycloak_admin``'s.

Keycloak is reached on its back channel, the issuer of the tokens being the address the browser
knows it by. A Keycloak that does not answer is a component unavailable (503); an answer that
breaks what the realm promises is a defect of the platform, raised as such.
"""

import math
import threading
import time
from collections.abc import Callable, Mapping
from functools import partial
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
# The algorithm the keys of the realm sign with; a token that says another one is refused.
ALGORITHMS = ("RS256",)
TIMEOUT_SECONDS = 10.0
# The keys are not read again before this delay has passed since the end of the last attempt: a
# token naming a key the realm never had, a Keycloak that does not answer, would otherwise send
# every request to Keycloak. A key the realm has just added is thus taken within this delay at
# worst; a failure to read them is given again until it has passed.
KEYS_REREAD_SECONDS = 10.0
# The keys are read again once they have been kept this long, the life of an access token of the
# realm: a key it has removed, a key it has stopped trusting, stops serving within this delay.
KEYS_MAX_AGE_SECONDS = 300.0

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


def expect(response: httpx2.Response, status: int) -> httpx2.Response:
    """Give an answer of Keycloak of the status the realm promises, or raise it as a defect."""
    if response.status_code != status:
        request = response.request
        message = f"{request.method} {request.url.path} answered {response.status_code}"
        raise IdentityProviderError(message)
    return response


class Keycloak:
    """The realm of Waterfall, as the API and the worker reach it."""

    def __init__(
        self,
        settings: ServiceSettings,
        clock: Callable[[], float] = time.monotonic,
        *,
        timeout: float = TIMEOUT_SECONDS,
        keys_reread: float = KEYS_REREAD_SECONDS,
    ) -> None:
        """Prepare the client; nothing is asked of Keycloak before a token is to be validated."""
        realm = quote(settings.keycloak_realm, safe="")
        self.issuer = f"{settings.keycloak_address.rstrip('/')}/realms/{realm}"
        backchannel = (settings.keycloak_backchannel or settings.keycloak_address).rstrip("/")
        self._http = httpx2.Client(base_url=backchannel, timeout=timeout)
        # Where the realm serves its keys and its tokens, on the back channel.
        self.protocol = f"/realms/{realm}/protocol/openid-connect"
        self._clock = clock
        self._keys_reread = keys_reread
        self._keys: Mapping[str, PyJWK] = {}
        # Until when the keys read are kept, and when they may be asked for again.
        self._keys_kept_until = -math.inf
        self._keys_reread_at = -math.inf
        # How the last attempt failed, given again until they may be asked for again.
        self._keys_failure: Callable[[], Exception] | None = None
        self._keys_lock = threading.Lock()

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

    def send(self, method: str, path: str, **options: Any) -> httpx2.Response:
        """Send a request to Keycloak on its back channel; refuse it while Keycloak fails (503)."""
        try:
            response = self._http.request(method, path, **options)
        except httpx2.HTTPError as error:
            logger.warning("identity_provider.unreachable", fault=type(error).__name__)
            raise unavailable() from None
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            logger.warning("identity_provider.failed", status=response.status_code)
            raise unavailable()
        return response

    def _key(self, key_id: str) -> PyJWK | None:
        key = self._keys.get(key_id)
        if key is not None and self._clock() < self._keys_kept_until:
            return key
        # A request whose key is held, even old, does not wait for the keys another one reads:
        # while Keycloak does not answer, that one alone waits.
        if not self._keys_lock.acquire(blocking=key is None):
            return key
        try:
            return self._key_held(key_id)
        finally:
            self._keys_lock.release()

    def _key_held(self, key_id: str) -> PyJWK | None:
        """Give the key of ``key_id``, reading the keys again if they may be; the lock is held."""
        # Another request may have read them while this one waited.
        now = self._clock()
        key = self._keys.get(key_id)
        if key is not None and now < self._keys_kept_until:
            return key
        if now < self._keys_reread_at:
            # Not a session missing while Keycloak has just failed to give the keys.
            if key is None and self._keys_failure is not None:
                raise self._keys_failure()
            return key
        try:
            keys = self._read_keys()
        except UnavailableError:
            self._keys_failure = unavailable
            if key is None:
                raise
            # The keys of a few minutes ago rather than a 503 at every request, while
            # Keycloak does not answer; they are asked for again in a while.
            logger.warning("identity_provider.keys_kept")
            return key
        except IdentityProviderError as error:
            self._keys_failure = partial(IdentityProviderError, str(error))
            raise
        finally:
            self._keys_reread_at = self._clock() + self._keys_reread
        self._keys = keys
        self._keys_kept_until = now + KEYS_MAX_AGE_SECONDS
        self._keys_failure = None
        return keys.get(key_id)

    def _read_keys(self) -> Mapping[str, PyJWK]:
        response = expect(self.send("GET", f"{self.protocol}/certs"), HTTPStatus.OK)
        try:
            keys = PyJWKSet.from_dict(cast("dict[str, Any]", response.json())).keys
        except (jwt.PyJWTError, AttributeError, ValueError) as error:
            message = "the keys of the realm are not usable"
            raise IdentityProviderError(message) from error
        return {key.key_id: key for key in keys if key.key_id and key.public_key_use != "enc"}
