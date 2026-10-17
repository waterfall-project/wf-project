# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a restoration asks of the identity provider, Keycloak, around the replacement of its base.

Its sessions closed, before and after, as its service account (WF-ADM-0160). Its caches cleared,
as the client of the bootstrap (#954), with the token that client took before the database was
replaced: the database restored holds the secrets of the clients of the source. The realm of the
installation applied again over the database restored (#955), by the service ``keycloak-realm``,
which a folder they alone share asks and answers: a request is a file ``<name>.request``, the answer
a file ``<name>.done``, or ``<name>.failed``. ``keycloak-realm`` then signs in to Keycloak as a
temporary administrator it makes in a container of its own — the server holds the port of
management —, applies the realm of the installation, gives the administrator of ``master`` its
password back, and removes the temporary administrator (#991). Last, the local accounts anonymised
again are removed from the realm that holds them again (#988).
"""

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import get_logger

# How long, in seconds, a realm applied again may take, and the pause between two looks.
PATIENCE = 600.0
PAUSE = 1.0

logger = get_logger(__name__)


class RealmNotAppliedError(RuntimeError):
    """The realm of the installation was not applied again over the database restored."""


class IdentityProvider(Protocol):
    """What a restoration asks of the identity provider."""

    def close_sessions(self) -> None:
        """Close every session of the realm."""

    def prepare(self) -> None:
        """Take, before its database is replaced, what clearing its caches needs."""

    def clear_caches(self) -> None:
        """Clear its caches, with what ``prepare`` took: it serves the database restored."""

    def apply_realm(self, name: str) -> None:
        """Apply the realm of the installation again over its database; ``name`` the asking."""

    def remove(self, subjects: Iterable[str]) -> None:
        """Remove accounts from the realm."""


@dataclass(frozen=True, slots=True)
class RealmRequests:
    """The folder where the restoration asks ``keycloak-realm`` to apply the realm again."""

    folder: Path
    patience: float = PATIENCE
    pause: float = PAUSE
    clock: Callable[[], float] = field(default=time.monotonic)
    sleep: Callable[[float], None] = field(default=time.sleep)

    def apply(self, name: str) -> None:
        """Ask for the realm applied again, and wait for the answer; fail if none, or a failure.

        The request is written under another name, then renamed: ``keycloak-realm`` never reads
        one half written. An answer an earlier asking of that name left is removed first.
        """
        done, failed = self.folder / f"{name}.done", self.folder / f"{name}.failed"
        for answer in (done, failed):
            answer.unlink(missing_ok=True)
        writing = self.folder / f".{name}.writing"
        writing.write_text(name, encoding="utf-8")
        writing.rename(self.folder / f"{name}.request")
        deadline = self.clock() + self.patience
        while self.clock() < deadline:
            if done.exists():
                done.unlink()
                return
            if failed.exists():
                failed.unlink()
                message = f"keycloak-realm did not apply the realm again ({name})"
                raise RealmNotAppliedError(message)
            self.sleep(self.pause)
        message = f"keycloak-realm did not answer in {self.patience:.0f} s ({name})"
        raise RealmNotAppliedError(message)


@dataclass(frozen=True, slots=True)
class Keycloak:
    """Keycloak, as a restoration asks it: its service account, the bootstrap client, its realm."""

    service: KeycloakAdmin
    installation: KeycloakAdmin
    realm: RealmRequests

    def close_sessions(self) -> None:
        """Close every session of the realm, as the service account."""
        self.service.close_every_session()

    def prepare(self) -> None:
        """Take the token of the client of the bootstrap, while the realm is the installation's."""
        self.installation.take_token()

    def clear_caches(self) -> None:
        """Clear the caches, as the client of the bootstrap, with the token it took before."""
        self.installation.clear_caches()

    def apply_realm(self, name: str) -> None:
        """Have ``keycloak-realm`` apply the realm of the installation again."""
        self.realm.apply(name)

    def remove(self, subjects: Iterable[str]) -> None:
        """Remove accounts from the realm, as the service account; an account gone is left."""
        removed = 0
        for subject in subjects:
            self.service.remove_account(subject)
            removed += 1
        if removed:
            logger.info("restore.accounts_removed_from_provider", count=removed)
