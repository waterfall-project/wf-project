# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The administration API of Keycloak, reached as the service account of the realm (PBS-2.5).

Through it the service reads where an account comes from, creates a local account and removes one
whose creation Waterfall could not complete, closes the sessions of an account (WF-ADM-0070,
WF-SEC-0020), and gives it the language its holder chose, that of its mails (WF-INTF-0160). The
link that sets the password of a local account is made by the extension of Waterfall, which also
mails it as the invitation of the account: never by ``execute-actions-email``, whose links would
escape its nonce (#651, WF-ADM-0140). The bootstrap finds the account of an address, tells whether
it has a password, and, as the client of the bootstrap, gives the realm the language of the
installation (#873) and asks the extension for the link of the installation, valid until it is
used (WF-EXP-0020, #652). The token of the client is kept until shortly before it expires.

Only Keycloak itself answers this API: what is here is tried against the Keycloak of the service
platform, whose tests measure it (``make test-keycloak``); the measure of the back, which runs no
Keycloak, leaves this module out by its path.
"""

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from typing import Any, Literal, cast
from urllib.parse import quote

import httpx2
from pydantic import SecretStr

from waterfall.platform.errors import FieldError, UnavailableError, UnprocessableError
from waterfall.platform.keycloak import IdentityProviderError, Keycloak, expect
from waterfall.platform.logs import get_logger
from waterfall.platform.settings import KeycloakSettings

SERVICE_CLIENT = "waterfall-service"
# The client of the bootstrap: the only one whose links are valid until they are used (#652).
INSTALLATION_CLIENT = "waterfall-installation"
# The token of the service account is renewed this long before it expires.
TOKEN_MARGIN_SECONDS = 30.0
VALIDATION_FAILED = "VALIDATION_FAILED"
# The attribute of an account of the realm that holds its language (WF-INTF-0160).
LOCALE = "locale"
# The field of a local identity each attribute of the realm holds, the username being its address.
IDENTITY_POINTERS = {
    "username": "/email",
    "email": "/email",
    "firstName": "/first_name",
    "lastName": "/last_name",
}

# Why the invitation of an account did not leave: the realm has no mail server, its server did not
# take the mail, or Keycloak does not answer.
type InvitationFailure = Literal["no_mail_server", "not_sent", "provider_unavailable"]

logger = get_logger(__name__)


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


@dataclass(frozen=True, slots=True)
class PasswordLink:
    """A link that sets the password of a local account, and when it stops being valid.

    A secret: whoever holds it sets the password. It is never logged nor kept (WF-SEC-0030).
    """

    url: str
    expires_at: datetime

    def __repr__(self) -> str:
        """Name the link without showing it."""
        return f"PasswordLink(expires_at={self.expires_at.isoformat()})"


@dataclass(frozen=True, slots=True)
class LocalIdentity:
    """What a local account of the realm is created with: its names and its address."""

    last_name: str
    first_name: str
    email: str


def _text(document: Mapping[str, Any], name: str) -> str:
    value = document.get(name)
    return value if isinstance(value, str) else ""


def _document(response: httpx2.Response) -> Mapping[str, Any]:
    """Read the object an answer carries, or an empty one if it carries none."""
    try:
        read: object = response.json()
    except ValueError:
        return {}
    return cast("Mapping[str, Any]", read) if isinstance(read, Mapping) else {}


def refused_identity(response: httpx2.Response) -> UnprocessableError | IdentityProviderError:
    """Point at the fields of a local identity the user profile of the realm refuses (422).

    The realm names one field, or a list of them under ``errors``; the username and the address
    are one field of the identity. A refusal that names none of its fields — an attribute the
    profile of the realm requires besides — is no value the user could correct: a defect of the
    platform, raised as such.
    """
    refusal = _document(response)
    errors = refusal.get("errors")
    named = cast("list[object]", errors) if isinstance(errors, list) and errors else [refusal]
    pointers = dict.fromkeys(pointer for error in named if (pointer := _pointer(error)))
    if not pointers:
        request = response.request
        message = f"{request.method} {request.url.path} answered 400 on no field of the identity"
        return IdentityProviderError(message)
    faults = tuple(FieldError(pointer, VALIDATION_FAILED) for pointer in pointers)
    return UnprocessableError(VALIDATION_FAILED, fields=faults)


def _not_local(response: httpx2.Response) -> bool:
    """Tell whether the extension refused a link to an account the realm holds as no local one."""
    return (
        response.status_code == HTTPStatus.CONFLICT
        and _document(response).get("error") == "not_local"
    )


def _pointer(error: object) -> str | None:
    named = _text(cast("Mapping[str, Any]", error), "field") if isinstance(error, Mapping) else ""
    return IDENTITY_POINTERS.get(named)


class KeycloakAdmin:
    """The administration API of the realm, reached through the client of Keycloak."""

    def __init__(
        self,
        keycloak: Keycloak,
        settings: KeycloakSettings,
        clock: Callable[[], float] = time.monotonic,
        *,
        client: tuple[str, SecretStr] | None = None,
    ) -> None:
        """Prepare the client; no token is asked for before a request needs one.

        It acts as the service account of Waterfall, unless ``client`` names another client of the
        realm and its secret: that of the bootstrap, for the link of the installation.
        """
        self._keycloak = keycloak
        realm = quote(settings.keycloak_realm, safe="")
        self._admin = f"/admin/realms/{realm}"
        # The entry point of the extension, under the realm (deploy/keycloak/extension/).
        self._extension = f"/realms/{realm}/password-setup-link"
        self._client, self._secret = client or (SERVICE_CLIENT, settings.service_client_secret)
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

    def create_account(self, identity: LocalIdentity) -> str | None:
        """Create a local account of the realm, without a password; give its subject.

        ``None`` if the realm holds an account of that address already, whose username it is.
        Refused if the user profile of the realm refuses a field of the identity (422).
        """
        response = self._as_service(
            "POST",
            f"{self._admin}/users",
            json={
                "username": identity.email,
                "email": identity.email,
                "firstName": identity.first_name,
                "lastName": identity.last_name,
                "enabled": True,
            },
        )
        if response.status_code == HTTPStatus.CONFLICT:
            return None
        if response.status_code == HTTPStatus.BAD_REQUEST:
            raise refused_identity(response)
        location = expect(response, HTTPStatus.CREATED).headers["Location"]
        return location.rstrip("/").rsplit("/", 1)[-1]

    def remove_account(self, subject: str) -> None:
        """Remove an account of the realm; one it no longer holds is removed already."""
        response = self._as_service("DELETE", f"{self._admin}/users/{quote(subject, safe='')}")
        if response.status_code != HTTPStatus.NOT_FOUND:
            expect(response, HTTPStatus.NO_CONTENT)

    def send_invitation(self, subject: str) -> InvitationFailure | None:
        """Have the extension mail a local account the link that sets its password (WF-ADM-0140).

        The link replaces the one made before it, unless the mail does not leave. Then the reason
        is given: the realm has no mail server — an installation without one gives the link by
        hand (WF-CMP-0030) —, its server did not take the mail, or Keycloak does not answer. The
        account exists all the same, and its link may be asked for again.
        """
        path = f"{self._extension}/users/{quote(subject, safe='')}/invitation"
        try:
            # The extension says by a 502 that the mail server failed; a proxy, that Keycloak did.
            response = self._as_service("POST", path, answered={HTTPStatus.BAD_GATEWAY})
        except UnavailableError:
            return "provider_unavailable"
        error = _document(response).get("error")
        if response.status_code == HTTPStatus.BAD_GATEWAY:
            if error == "not_sent":
                return "not_sent"
            # Not the extension's: a proxy says Keycloak failed, as ``Keycloak.send`` logs it.
            logger.warning("identity_provider.failed", status=response.status_code)
            return "provider_unavailable"
        if response.status_code == HTTPStatus.CONFLICT and error == "no_mail_server":
            return "no_mail_server"
        expect(response, HTTPStatus.NO_CONTENT)
        return None

    def make_password_link(self, subject: str) -> PasswordLink | None:
        """Have the extension make the link that sets the password of a local account.

        Valid one hour and once, it replaces the one made before it (WF-ADM-0140). ``None`` if the
        realm holds the account as no local one: read from a directory, or relayed by an external
        provider since Waterfall created it. An account the realm no longer holds is a defect.
        """
        path = f"{self._extension}/users/{quote(subject, safe='')}"
        response = self._as_service("POST", path)
        if _not_local(response):
            return None
        made = _document(expect(response, HTTPStatus.OK))
        url, expires_at = _text(made, "url"), _text(made, "expires_at")
        try:
            moment = datetime.fromisoformat(expires_at)
        except ValueError:
            moment = None
        if not url or moment is None or moment.tzinfo is None:
            message = f"POST {response.request.url.path} answered no link"
            raise IdentityProviderError(message)
        return PasswordLink(url, moment)

    def find_account(self, email: str) -> str | None:
        """Give the subject of the account of the realm that holds ``email``, or ``None``."""
        response = self._as_service(
            "GET", f"{self._admin}/users", params={"email": email, "exact": "true"}
        )
        found = cast("list[Mapping[str, Any]]", expect(response, HTTPStatus.OK).json())
        for user in found:
            if _text(user, "email").lower() == email.lower():
                return _text(user, "id") or None
        return None

    def has_password(self, subject: str) -> bool | None:
        """Tell whether an account of the realm has a password, or ``None`` if it has no account."""
        path = f"{self._admin}/users/{quote(subject, safe='')}/credentials"
        response = self._as_service("GET", path)
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        held = cast("list[Mapping[str, Any]]", expect(response, HTTPStatus.OK).json())
        return any(_text(credential, "type") == "password" for credential in held)

    def make_installation_link(self, subject: str) -> str | None:
        """Have the extension make the link of the installation, valid until it is used.

        Asked as the client of the bootstrap, which alone may (WF-EXP-0020, #652); the link replaces
        the one made before it, as any link does. ``None`` if the realm holds the account as no
        local one.
        """
        path = f"{self._extension}/users/{quote(subject, safe='')}"
        response = self._as_service("POST", path)
        if _not_local(response):
            return None
        url = _text(_document(expect(response, HTTPStatus.OK)), "url")
        if not url:
            message = f"POST {response.request.url.path} answered no link"
            raise IdentityProviderError(message)
        return url

    def set_default_language(self, language: str) -> None:
        """Give the realm ``language`` as its own, that of an account that chose none (#873).

        Asked as the client of the bootstrap, which alone may change the realm (WF-INTF-0160).
        """
        response = self._as_service("PUT", self._admin, json={"defaultLocale": language})
        expect(response, HTTPStatus.NO_CONTENT)

    def close_sessions(self, subject: str) -> None:
        """Close every session of an account, on every device (WF-SEC-0020).

        An account the realm no longer holds has no session left to close.
        """
        response = self._as_service("POST", f"{self._admin}/users/{quote(subject, safe='')}/logout")
        if response.status_code != HTTPStatus.NOT_FOUND:
            expect(response, HTTPStatus.NO_CONTENT)

    def set_locale(self, subject: str, locale: str | None) -> None:
        """Give an account of the realm the language it mails and shows its pages in.

        ``None`` withdraws it: the realm then speaks its own language by default. An account the
        realm no longer holds has no language left to set. The account is read, then written back
        whole with its attribute ``locale`` changed: the realm keeps only the attributes it is sent.
        """
        user = f"{self._admin}/users/{quote(subject, safe='')}"
        response = self._as_service("GET", user)
        if response.status_code == HTTPStatus.NOT_FOUND:
            return
        held = dict(cast("Mapping[str, Any]", expect(response, HTTPStatus.OK).json()))
        attributes = dict(cast("Mapping[str, list[str]]", held.get("attributes") or {}))
        if locale is None:
            attributes.pop(LOCALE, None)
        else:
            attributes[LOCALE] = [locale]
        written = self._as_service("PUT", user, json={**held, "attributes": attributes})
        if written.status_code != HTTPStatus.NOT_FOUND:
            expect(written, HTTPStatus.NO_CONTENT)

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
                    "client_id": self._client,
                    "client_secret": self._secret.get_secret_value(),
                },
            )
            granted = cast("Mapping[str, Any]", expect(response, HTTPStatus.OK).json())
            token = cast("str", granted["access_token"])
            lifetime = float(granted["expires_in"])
            self._token = (token, asked_at + lifetime - TOKEN_MARGIN_SECONDS)
            return token

    def _as_service(self, method: str, path: str, **options: Any) -> httpx2.Response:
        """Send a request of the administration API as the service account.

        A token refused before its time — the realm restarted, its keys rotated, the sessions
        of the service account closed — is renewed once.
        """
        response = self._send(method, path, self._service_token(), **options)
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            response = self._send(method, path, self._service_token(renew=True), **options)
        return response

    def _send(self, method: str, path: str, token: str, **options: Any) -> httpx2.Response:
        headers = {"Authorization": f"Bearer {token}"}
        return self._keycloak.send(method, path, headers=headers, **options)
