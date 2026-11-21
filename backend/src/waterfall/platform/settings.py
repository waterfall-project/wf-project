# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Settings and secrets, read from the environment at start (WF-SEC-0010).

A secret that is missing stops the process and names the variable that lacks, rather than
letting the service start without it. The secrets are ``SecretStr``: printing the settings
shows no value.
"""

from contextlib import suppress
from functools import cache
from typing import Annotated, Any, Literal
from urllib.parse import unquote, unquote_plus, urlsplit
from zoneinfo import available_timezones

from pydantic import AfterValidator, BeforeValidator, Field, SecretStr, ValidationError
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
    """What a service of the platform reads besides: Redis, and where it listens.

    ``host`` is the address the API listens on, and the worker for its metrics.
    ``indicators_cache_ttl`` is how long an entry of the cache of the indicators stays valid, in
    seconds: ten minutes by default (WF-DAT-0130-A).
    """

    redis_url: SecretStr = Field(min_length=1)
    indicators_cache_ttl: int = Field(default=600, ge=1)
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


class StorageSettings(PlatformSettings):
    """What a process that reaches the object storage reads (PBS-3.3, WF-ARC-0050).

    Its address, its region, the key of the platform, and the bucket of the backups — settings, so
    that an operator plugs in the storage they already run. The files in transit and the exports
    lie in that bucket, under their prefixes (EP-06, "Ce que le cadrage décide").
    """

    storage_address: str = Field(min_length=1, pattern="^https?://")
    storage_region: str = Field(default="us-east-1", min_length=1)
    storage_access_key: str = Field(min_length=1)
    storage_secret: SecretStr = Field(min_length=1)
    backups_bucket: str = Field(default="backups", min_length=1)


class ServiceSettings(Settings, KeycloakSettings, StorageSettings):
    """What a service that reaches Keycloak reads: the API, and the worker after it."""


class ApiSettings(ServiceSettings):
    """What the API reads besides: on how many processes it serves (US-2230), and its capacities.

    ``api_processes`` is the number of the processes of uvicorn that serve the requests, each with
    its own services and its own reserve of connections to the database: one by default, so that
    the tests and the workstation serve on the process that starts them.
    ``database_capacity_bytes`` and ``storage_capacity_bytes`` are the space the deployment gives
    PostgreSQL and the object storage, in bytes, of which the metrics say what is left
    (WF-OBS-0010): none by default, and then they say only what is used.
    """

    api_processes: int = Field(default=1, ge=1)
    database_capacity_bytes: int | None = Field(default=None, ge=1)
    storage_capacity_bytes: int | None = Field(default=None, ge=1)


class ScheduleSettings(Settings):
    """What ``waterfall-worker schedule`` reads: the database and Redis, nothing else (TFX-10).

    ``identity_sync_interval`` is how long the platform waits between two readings of the accounts,
    in seconds, a day by default (PBS-5.3; US-3040 replaces it by the planning the administrator
    sets), and ``purge_interval`` between two purges of what expired, ten minutes by default (EP-06,
    "La purge"). A task is deposited when the latest of its kind was submitted at least that long
    ago. The purge spares the latest task of each planned kind, however old, so that an interval
    longer than the retention of the tasks does not make a reading due again at each purge. Under
    Helm the first reading may leave before the realm of Keycloak is applied (a hook after the
    installation): it then fails and the next is due an interval later.
    """

    identity_sync_interval: int = Field(default=86_400, ge=1)
    purge_interval: int = Field(default=600, ge=1)


class WorkerSettings(ServiceSettings):
    """What the worker reads besides: the two databases a backup dumps, as the role of the backup.

    ``metrics_port`` is where it serves its metrics, on the address of ``host`` (WF-OBS-0010).
    The purge it runs keeps the history of a session ``undo_retention_hours`` hours, twelve by
    default: the longest session of the realm (EP-06, "L'historique annulable et le collage"); and
    a task ended ``background_task_retention_days`` days, thirty by default, the retention of its
    result (WF-DAT-0080, §4.4.1), the operating parameter of the same name.
    ``backup_database_url`` is the database of Waterfall, the journal of audit included, and
    ``keycloak_database_url`` the database of the identity provider, both as the role of the backup
    reaches them: a member of ``pg_read_all_data``, which reads every table and can neither write
    nor turn a trigger off (#895). Never the owner of the tables, who could give itself back the
    rights or turn off the trigger of the journal, nor a superuser (#701). The worker connects by
    either to dump alone.
    """

    backup_database_url: SecretStr = Field(min_length=1)
    keycloak_database_url: SecretStr = Field(min_length=1)
    metrics_port: int = Field(default=9100, ge=1, le=65535)
    undo_retention_hours: int = Field(default=12, ge=1)
    background_task_retention_days: int = Field(default=30, ge=1)


@cache
def _time_zones() -> frozenset[str]:
    return frozenset(available_timezones())


def _known_time_zone(name: str) -> str:
    """Keep the name of a time zone of the IANA database (``Europe/Paris``); refuse another."""
    if name not in _time_zones():
        message = "is not a time zone of the IANA database"
        raise ValueError(message)
    return name


def _known_time_zone_if_given(name: str | None) -> str | None:
    """Keep a name given, if the IANA database knows it; none is none."""
    return None if name is None else _known_time_zone(name)


def _none_when_empty(value: object) -> object:
    """Read an empty setting as one not given: Compose passes an unset variable as empty."""
    return None if value == "" else value


class InstallationSettings(KeycloakSettings):
    """What the bootstrap of an installation reads, ``waterfall-api install`` (US-0420).

    ``database_url`` designates the owner of the tables, who applies the migrations (#701);
    ``installation_client_secret`` is the secret of the client of the bootstrap, the only one that
    makes a link valid until it is used, which neither the API nor the worker holds (#652);
    ``admin_email`` the address of the first administrator, and ``default_language`` the language
    of the installation (WF-EXP-0020, WF-INTF-0160); ``currency`` its single currency, three
    capital letters (WF-REF-0140), and ``company_name`` the name of the company that uses it, from
    1 to 200 characters and never blank (WF-EXP-0020), both written once, at the first run;
    ``time_zone`` the name of its time zone in the IANA database, optional, in which the
    current day is taken (WF-EXP-0020, WF-PLA-0130, US-2200), written once too, ``UTC`` when none is
    given at that first writing — the bootstrap refuses a name it
    does not know. It deposits no task and serves nothing: it reads neither Redis nor where the API
    listens.
    """

    installation_client_secret: SecretStr = Field(min_length=1)
    admin_email: str = Field(min_length=1)
    default_language: Literal["fr", "en"]
    currency: str = Field(pattern="^[A-Z]{3}$")
    company_name: str = Field(min_length=1, max_length=200, pattern=r"\S")
    time_zone: Annotated[
        str | None, BeforeValidator(_none_when_empty), AfterValidator(_known_time_zone_if_given)
    ] = None


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


class WitnessSettings(PlatformSettings):
    """What the loader of the witness reads, ``waterfall-api load-witness`` (WF-QUA-0040, EP-05).

    ``database_url`` designates the role of the service: the loader writes through the interfaces
    of the modules, as the service does, never as the owner of the tables. ``witness_path`` is the
    directory of the description of the witness, the examples of the contract (``fixtures/api``).
    It reaches neither Redis nor Keycloak.
    """

    witness_path: str = Field(min_length=1)


def load_settings() -> Settings:
    """Read the settings from the environment, or raise a ``SettingsError`` that names each fault.

    The message names the variables and what is wrong with them, never the values they hold.
    """
    return _load(Settings)


def load_platform_settings() -> PlatformSettings:
    """Read what every process reads, its database and its logs, as ``load_settings`` does."""
    return _load(PlatformSettings)


def load_schedule_settings() -> ScheduleSettings:
    """Read the settings of the schedule, as ``load_settings`` does."""
    return _load(ScheduleSettings)


def load_service_settings() -> ServiceSettings:
    """Read the settings of a process that reaches Keycloak, as ``load_settings`` does."""
    return _load(ServiceSettings)


def load_api_settings() -> ApiSettings:
    """Read the settings of the API, as ``load_settings`` does."""
    return _load(ApiSettings)


def load_worker_settings() -> WorkerSettings:
    """Read the settings of the worker, as ``load_settings`` does."""
    return _load(WorkerSettings)


def load_restore_settings() -> RestoreSettings:
    """Read the settings of the service of the restoration, as ``load_settings`` does."""
    return _load(RestoreSettings)


def load_installation_settings() -> InstallationSettings:
    """Read the settings of the bootstrap, as ``load_settings`` does."""
    return _load(InstallationSettings)


def load_witness_settings() -> WitnessSettings:
    """Read the settings of the loader of the witness, as ``load_settings`` does."""
    return _load(WitnessSettings)


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
