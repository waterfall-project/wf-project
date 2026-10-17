# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Settings and secrets, read from the environment at start (WF-SEC-0010).

A secret that is missing stops the process and names the variable that lacks, rather than
letting the service start without it. The secrets are ``SecretStr``: printing the settings
shows no value.
"""

from contextlib import suppress
from typing import Any, Literal
from urllib.parse import unquote, unquote_plus, urlsplit

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "WATERFALL_"


class SettingsError(Exception):
    """The environment does not give the settings the service needs."""


MIN_DECODED_LENGTH = 4


def _url_secrets(value: str) -> list[str]:
    """Give what a URL carries as a secret: its password as written and as a driver decodes it.

    The password is read from the text first, for every ``@`` after the scheme: what follows the
    first ``:`` of what precedes it. ``urlsplit`` cuts the address at an unencoded ``#``, ``/``
    or ``?`` and then finds no password, or refuses the URL; and an ``@`` in the query leaves
    no way to tell which one ends the credentials, so each is taken, at the price of masking
    more. A decoded form shorter than ``MIN_DECODED_LENGTH`` characters is not kept, and nor is a
    fragment of the text: it would hide every text that contains it. Only the password that
    ``urlsplit`` returns is kept whatever its length.
    """
    rest = value.partition("://")[2]
    passwords = [
        fragment
        for index, char in enumerate(rest)
        if char == "@" and len(fragment := rest[:index].partition(":")[2]) >= MIN_DECODED_LENGTH
    ]
    with suppress(ValueError):
        passwords.append(urlsplit(value).password or "")
    found: list[str] = []
    for password in dict.fromkeys(passwords):
        if not password:
            continue
        decoded = [unquote(password), unquote_plus(password)]
        found += [password, *(text for text in decoded if len(text) >= MIN_DECODED_LENGTH)]
    return found


class PlatformSettings(BaseSettings):
    """What every process of the platform reads from its environment: its database, its logs."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    database_url: SecretStr = Field(min_length=1)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    def secret_values(self) -> tuple[str, ...]:
        """Give every secret held, and the password a URL secret carries, for the logs to mask.

        A driver quotes the password alone as readily as the address: both are secrets.
        """
        values = (getattr(self, name) for name in type(self).model_fields)
        held = [value.get_secret_value() for value in values if isinstance(value, SecretStr)]
        extra = [part for value in held for part in _url_secrets(value)]
        return tuple(dict.fromkeys(value for value in [*held, *extra] if value))


class Settings(PlatformSettings):
    """What a service of the platform reads besides: Redis, and where the API listens."""

    redis_url: SecretStr = Field(min_length=1)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)


class KeycloakSettings(PlatformSettings):
    """What a process that reaches Keycloak reads besides.

    ``keycloak_address`` is where the browser reaches Keycloak, which names the issuer of every
    token whoever asks for it; ``keycloak_backchannel`` is where this process reaches it, for its
    keys and its administration API — the same address unless a network of the platform gives
    another one. ``service_client_secret`` is the secret of the service account of the realm.
    """

    keycloak_address: str = Field(min_length=1, pattern="^https?://")
    keycloak_backchannel: str | None = Field(default=None, min_length=1, pattern="^https?://")
    keycloak_realm: str = Field(default="waterfall", pattern="^[A-Za-z0-9_-]+$")
    service_client_secret: SecretStr = Field(min_length=1)


class ServiceSettings(Settings, KeycloakSettings):
    """What a service that reaches Keycloak reads: the API, and the worker after it."""

    # The object storage, reached by the standard operations of S3 (PBS-3.3): its address, its
    # region, the key of the platform, and the bucket of the backups — settings, so that an operator
    # plugs in the storage they already run (WF-ARC-0050).
    storage_address: str = Field(min_length=1, pattern="^https?://")
    storage_region: str = Field(default="us-east-1", min_length=1)
    storage_access_key: str = Field(min_length=1)
    storage_secret: SecretStr = Field(min_length=1)
    backups_bucket: str = Field(default="backups", min_length=1)


class WorkerSettings(ServiceSettings):
    """What the worker reads besides: the two databases a backup dumps, as the role of the backup.

    ``backup_database_url`` is the database of Waterfall, the journal of audit included, and
    ``keycloak_database_url`` the database of the identity provider, both as the role of the backup
    reaches them: a member of ``pg_read_all_data``, which reads every table and can neither write
    nor turn a trigger off (#895). Never the owner of the tables, who could give itself back the
    rights or turn off the trigger of the journal, nor a superuser (#701). The worker connects by
    either to dump alone.
    """

    backup_database_url: SecretStr = Field(min_length=1)
    keycloak_database_url: SecretStr = Field(min_length=1)


class InstallationSettings(KeycloakSettings):
    """What the bootstrap of an installation reads, ``waterfall-api install`` (US-0420).

    ``database_url`` designates the owner of the tables, who applies the migrations (#701);
    ``installation_client_secret`` is the secret of the client of the bootstrap, the only one that
    makes a link valid until it is used, which neither the API nor the worker holds (#652);
    ``admin_email`` the address of the first administrator, and ``default_language`` the language
    of the installation (WF-EXP-0020, WF-INTF-0160). It deposits no task and serves nothing: it
    reads neither Redis nor where the API listens.
    """

    installation_client_secret: SecretStr = Field(min_length=1)
    admin_email: str = Field(min_length=1)
    default_language: Literal["fr", "en"]


class RestoreSettings(ServiceSettings):
    """What the service of the restoration reads, ``waterfall-restore`` (WF-ADM-0160, #953).

    The only process of the platform that holds the owners of both databases: ``database_url``
    designates the owner of the tables of Waterfall, who replaces them and applies the migrations,
    and ``keycloak_database_url`` the owner of the database of the identity provider (#701).
    ``installation_client_secret`` is the secret of the client of the bootstrap, whose account
    clears the caches of the realm (``manage-realm``, #954); ``service_client_secret``, that of the
    service account, which closes the sessions. ``realm_requests`` is the folder it shares with the
    service ``keycloak-realm`` alone, where it asks for the realm of the installation to be applied
    again over the database restored, and reads the answer (#955).
    """

    keycloak_database_url: SecretStr = Field(min_length=1)
    installation_client_secret: SecretStr = Field(min_length=1)
    realm_requests: str = Field(min_length=1)


def load_settings() -> Settings:
    """Read the settings from the environment, or raise a ``SettingsError`` that names each fault.

    The message names the variables and what is wrong with them, never the values they hold.
    """
    return _load(Settings)


def load_service_settings() -> ServiceSettings:
    """Read the settings of a process that reaches Keycloak, as ``load_settings`` does."""
    return _load(ServiceSettings)


def load_worker_settings() -> WorkerSettings:
    """Read the settings of the worker, as ``load_settings`` does."""
    return _load(WorkerSettings)


def load_restore_settings() -> RestoreSettings:
    """Read the settings of the service of the restoration, as ``load_settings`` does."""
    return _load(RestoreSettings)


def load_installation_settings() -> InstallationSettings:
    """Read the settings of the bootstrap, as ``load_settings`` does."""
    return _load(InstallationSettings)


def _load[Kind: PlatformSettings](kind: type[Kind]) -> Kind:
    # The values come from the environment, which pydantic-settings reads itself.
    from_environment: dict[str, Any] = {}
    try:
        return kind(**from_environment)
    except ValidationError as error:
        faults = [
            f"{ENV_PREFIX}{'_'.join(str(part) for part in fault['loc']).upper()}: "
            + ("is missing" if fault["type"] == "missing" else fault["msg"])
            for fault in error.errors(include_input=False, include_url=False)
        ]
        message = "settings are not valid: " + "; ".join(faults)
        raise SettingsError(message) from None
