# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Settings and secrets, read from the environment at start (WF-SEC-0010).

A secret that is missing stops the process and names the variable that lacks, rather than
letting the service start without it. The secrets are ``SecretStr``: printing the settings
shows no value.

The transport (US-2840): ``tls_authority`` names the file of the roots a process trusts for the
exchanges inside the platform, the root of its authority. Given, it must be read, and every address
of a component of data must be encrypted — PostgreSQL with ``sslmode=verify-full``, which checks
the certificate and its name, Redis in ``rediss://``, the object storage and Keycloak in
``https://`` —, with no parameter that turns the check off or loosens it, or the process stops,
naming what is wrong. PostgreSQL and Redis read the root from their address, as their drivers do
(``sslrootcert``, ``ssl_ca_certs``); the clients of Keycloak and of the storage, from this setting.
Not given, the addresses are taken as they are: the workstation and the tests reach their
components on the loopback.
"""

import json
import ssl
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal, Self
from urllib.parse import parse_qs, unquote, unquote_plus, urlsplit
from zoneinfo import available_timezones

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PrivateAttr,
    SecretStr,
    ValidationError,
    model_validator,
)
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


def _none_when_empty(value: object) -> object:
    """Read an empty setting as one not given: Compose passes an unset variable as empty."""
    return None if value == "" else value


def _roots(path: str | None) -> str | None:
    """Keep the path of a file of certificates in PEM that can be read; refuse another."""
    if path is None:
        return None
    if not Path(path).is_file():
        message = f"no file at {path}"
        raise ValueError(message)
    try:
        ssl.create_default_context(cafile=path)
    except (OSError, ssl.SSLError) as error:
        message = f"{path} is not a file of certificates in PEM that can be read"
        raise ValueError(message) from error
    return path


type Roots = Annotated[str | None, BeforeValidator(_none_when_empty), AfterValidator(_roots)]


def _query(address: str) -> dict[str, list[str]] | None:
    """Read the parameters of an address, each name in lower case; None if it does not read."""
    try:
        parsed = parse_qs(urlsplit(address).query, keep_blank_values=True)
    except ValueError:
        return None
    query: dict[str, list[str]] = {}
    for name, values in parsed.items():
        query.setdefault(name.lower(), []).extend(values)
    return query


def verifies_postgresql(address: str) -> bool:
    """Tell whether an address of PostgreSQL asks libpq to check the certificate and its name.

    Every ``sslmode`` it gives is ``verify-full``, whichever libpq would keep. ``gssencmode`` other
    than ``disable`` is refused too: libpq prefers the encryption of GSSAPI where it can, and then
    checks no certificate, whatever ``sslmode`` says.
    """
    query = _query(address)
    if query is None:
        return False
    modes = query.get("sslmode", [])
    return (
        bool(modes)
        and all(mode == "verify-full" for mode in modes)
        and all(mode == "disable" for mode in query.get("gssencmode", []))
    )


REDIS_TRUE = frozenset({"1", "T", "TRUE", "Y", "YES"})
"""What redis-py reads as true in an address: the other values turn a check off."""


def _keeps_the_check(name: str, value: str) -> bool:
    """Tell whether a parameter ``ssl_*`` of an address of Redis leaves the check whole."""
    if name == "ssl_ca_certs":
        return True
    if name == "ssl_cert_reqs":
        return value == "required"
    if name == "ssl_check_hostname":
        return value.upper() in REDIS_TRUE
    return False


def verifies_redis(address: str) -> bool:
    """Tell whether an address of Redis asks redis-py for TLS, the certificate and its name checked.

    In ``rediss://``, redis-py checks both by default; a parameter of the address can turn either
    off (``ssl_cert_reqs=none``, ``ssl_check_hostname=false``), or loosen what is checked (the flags
    of the check, the versions, the ciphers). Of the parameters ``ssl_*``, only the file of the
    roots, ``ssl_cert_reqs=required`` and ``ssl_check_hostname`` true are admitted.
    """
    query = _query(address)
    if query is None or not address.startswith("rediss://"):
        return False
    return all(
        _keeps_the_check(name, value)
        for name, values in query.items()
        if name.startswith("ssl")
        for value in values
    )


def encrypted_fault(name: str, *, encrypted: bool, wanted: str) -> list[str]:
    """Say how a setting of an address fails the transport the authority asks, if it does."""
    if encrypted:
        return []
    return [f"{ENV_PREFIX}{name.upper()} must {wanted} when {ENV_PREFIX}TLS_AUTHORITY is given"]


class PlatformSettings(BaseSettings):
    """What every process of the platform reads from its environment: its database, its logs.

    ``tls_authority`` is the file of the roots it trusts inside the platform (US-2840), none by
    default; given, each address of PostgreSQL the process reads must check the certificate.
    """

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    database_url: SecretStr = Field(min_length=1)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    tls_authority: Roots = None

    def transport_faults(self) -> list[str]:
        """Say each address that would be reached in the clear, though an authority is given.

        Each class adds the addresses it reads; every address of PostgreSQL is found by its name.
        """
        return [
            fault
            for name in type(self).model_fields
            if name.endswith("database_url")
            for fault in encrypted_fault(
                name,
                encrypted=verifies_postgresql(getattr(self, name).get_secret_value()),
                wanted="ask sslmode=verify-full, and no other sslmode nor gssencmode",
            )
        ]

    @model_validator(mode="after")
    def _encrypted(self) -> Self:
        if self.tls_authority is not None and (faults := self.transport_faults()):
            raise ValueError("; ".join(faults))
        return self

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

    def transport_faults(self) -> list[str]:
        """Add Redis, which must be reached in ``rediss://``, its certificate checked."""
        encrypted = verifies_redis(self.redis_url.get_secret_value())
        wanted = (
            "be in rediss://, with no parameter ssl_ but ssl_ca_certs, ssl_cert_reqs=required "
            "and ssl_check_hostname=true"
        )
        return [
            *super().transport_faults(),
            *encrypted_fault("redis_url", encrypted=encrypted, wanted=wanted),
        ]


class RealmSettings(PlatformSettings):
    """The realm of the installation, whose accounts a backup counts and its test counts again.

    The one place the default realm is written (#4662): the backup, the test of a restoration and
    the processes that reach Keycloak all read ``keycloak_realm`` from here.
    """

    keycloak_realm: str = Field(default="waterfall", pattern="^[A-Za-z0-9_-]+$")


class KeycloakSettings(RealmSettings):
    """What a process that reaches Keycloak reads besides.

    ``keycloak_address`` is where the browser reaches Keycloak, which names the issuer of every
    token whoever asks for it; ``keycloak_backchannel`` is where this process reaches it, for its
    keys and its administration API — the same address unless a network of the platform gives
    another one. ``service_client_secret`` is the secret of the service account of the realm.
    """

    keycloak_address: str = Field(min_length=1, pattern="^https?://")
    keycloak_backchannel: str | None = Field(default=None, min_length=1, pattern="^https?://")
    service_client_secret: SecretStr = Field(min_length=1)

    def transport_faults(self) -> list[str]:
        """Add the address this process reaches Keycloak at, which must be in ``https://``."""
        name = "keycloak_address" if self.keycloak_backchannel is None else "keycloak_backchannel"
        encrypted = (self.keycloak_backchannel or self.keycloak_address).startswith("https://")
        wanted = "be in https://"
        return [
            *super().transport_faults(),
            *encrypted_fault(name, encrypted=encrypted, wanted=wanted),
        ]


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

    def transport_faults(self) -> list[str]:
        """Add the object storage, which must be reached in ``https://``."""
        encrypted = self.storage_address.startswith("https://")
        wanted = "be in https://"
        return [
            *super().transport_faults(),
            *encrypted_fault("storage_address", encrypted=encrypted, wanted=wanted),
        ]


# The external locations of the backups (US-2910/L3): declared in a file the deployment mounts.

# The name of a location, a key of the file (`ExternalBackupLocationName`).
# What botocore takes for a region: a label of a host name.
REGION = "^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
LOCATION_NAME = "^[a-z0-9][a-z0-9_-]{0,62}$"
# The longest description the contract presents (`ExternalBackupLocation.description`).
DESCRIPTION_LENGTH = 500


class S3Location(BaseModel):
    """A bucket of an S3 storage, on another site: where it is, and the key that writes in it.

    ``address`` is the endpoint of the storage, ``bucket`` the bucket the copies go to;
    ``access_key`` and ``secret_key`` sign the requests, secrets both. ``authority`` is the file of
    the roots its certificate is checked against, the usual ones when it is not given.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["s3"]
    description: str | None = Field(default=None, max_length=DESCRIPTION_LENGTH)
    address: str = Field(pattern="^https?://")
    region: str = Field(default="us-east-1", pattern=REGION)
    bucket: str = Field(min_length=1)
    access_key: SecretStr = Field(min_length=1)
    secret_key: SecretStr = Field(min_length=1)
    authority: Roots = None

    @model_validator(mode="after")
    def _address_without_credentials(self) -> Self:
        """Refuse an address that is not an endpoint: no host, credentials, query or fragment.

        The key and its secret are fields apart; a token in a parameter is a credential as well.
        Never the value itself in the message.
        """
        try:
            parts = urlsplit(self.address)
            host = parts.hostname
            _ = parts.port  # reading the port checks it
        except ValueError:
            message = "the address does not read as a URL"
            raise ValueError(message) from None
        if not host:
            message = "the address must name a host"
            raise ValueError(message)
        if parts.query or parts.fragment or "?" in self.address or "#" in self.address:
            message = "the address must carry no query nor fragment: it is an endpoint"
            raise ValueError(message)
        if parts.username is not None or parts.password is not None:
            message = "the address must not carry credentials: give them as access_key, secret_key"
            raise ValueError(message)
        return self

    def secrets(self) -> tuple[str, ...]:
        """Give what the logs must never show of it: its key and the secret of the key."""
        return (self.access_key.get_secret_value(), self.secret_key.get_secret_value())


class MountedShare(BaseModel):
    """A network share mounted on the server: the folder, absolute, where it is mounted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["mounted_share"]
    description: str | None = Field(default=None, max_length=DESCRIPTION_LENGTH)
    directory: str = Field(pattern="^/")

    def secrets(self) -> tuple[str, ...]:
        """Give what the logs must never show of it: nothing, the mount holds its credentials."""
        return ()


type DeclaredLocation = Annotated[S3Location | MountedShare, Field(discriminator="kind")]


class ExternalLocations(BaseModel):
    """The external locations an installation declares, by their name (WF-ADM-0170).

    Read from a file in JSON that the deployment mounts, an object whose keys are the names: each
    with its nature, its description, and what reaches it — secrets included, which only the server
    reads, and which no reading of the API, no log and no error gives back
    (`ExternalBackupLocation`). None declared, an installation offers no copy.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    locations: dict[Annotated[str, Field(pattern=LOCATION_NAME)], DeclaredLocation] = Field(
        default_factory=dict
    )

    def declared(self) -> list[tuple[str, DeclaredLocation]]:
        """Give the locations declared, in the order of their names."""
        return sorted(self.locations.items())

    def names(self) -> frozenset[str]:
        """Give the names of the locations declared."""
        return frozenset(self.locations)

    def get(self, name: str) -> DeclaredLocation | None:
        """Give the location of a name, or ``None`` if none is declared under it."""
        return self.locations.get(name)

    def secrets(self) -> tuple[str, ...]:
        """Give the secrets of every location, for the logs to mask."""
        return tuple(secret for _, each in self.declared() for secret in each.secrets())


# An installation that declares none, as it is without a file.
NO_LOCATIONS = ExternalLocations()
LOCATIONS_VARIABLE = f"{ENV_PREFIX}EXTERNAL_BACKUP_LOCATIONS_FILE"


def read_external_locations(path: Path) -> ExternalLocations:
    """Read the external locations a file declares; refuse a file that does not declare them.

    The refusal names the variable, the file and the place of each fault, and its rule, never a
    value the file holds: a secret badly placed would else be written to the journal of the start.
    """
    try:
        read = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        message = f"{LOCATIONS_VARIABLE}: {path} cannot be read ({type(error).__name__})"
        raise ValueError(message) from None
    except json.JSONDecodeError as error:
        where = f"line {error.lineno}, column {error.colno}"
        message = f"{LOCATIONS_VARIABLE}: {path} is not JSON ({error.msg}, {where})"
        raise ValueError(message) from None
    try:
        return ExternalLocations.model_validate({"locations": read})
    except ValidationError as error:
        faults = [
            f"{'.'.join(str(part) for part in fault['loc'][1:]) or 'the file'}: {fault['msg']}"
            for fault in error.errors(include_input=False, include_url=False, include_context=False)
        ]
        message = f"{LOCATIONS_VARIABLE}: {path} does not declare locations: " + "; ".join(faults)
        raise ValueError(message) from None


class ServiceSettings(Settings, KeycloakSettings, StorageSettings):
    """What a service that reaches Keycloak reads: the API, and the worker after it.

    ``background_task_retention_days`` is how long the result of a task ended is kept, thirty days
    by default (WF-DAT-0080, §4.4.1): an operating parameter, which the worker's purge applies and
    the status screen presents.
    """

    background_task_retention_days: int = Field(default=30, ge=1)
    # The file of the external locations of the backups (US-2910/L3), read at start: none by
    # default, and then no location is declared. A bucket reached in the clear is refused when an
    # authority is given, as every other address is (US-2840).
    external_backup_locations_file: Annotated[str | None, BeforeValidator(_none_when_empty)] = None
    _external_locations: ExternalLocations = PrivateAttr(default=NO_LOCATIONS)

    @model_validator(mode="after")
    def _locations_declared(self) -> Self:
        if self.external_backup_locations_file is None:
            return self
        declared = read_external_locations(Path(self.external_backup_locations_file))
        clear = [
            name
            for name, each in declared.declared()
            if isinstance(each, S3Location) and not each.address.startswith("https://")
        ]
        if self.tls_authority is not None and clear:
            message = (
                f"{LOCATIONS_VARIABLE}: the address of {', '.join(clear)} must be in https:// "
                f"when {ENV_PREFIX}TLS_AUTHORITY is given"
            )
            raise ValueError(message)
        self._external_locations = declared
        return self

    @property
    def external_locations(self) -> ExternalLocations:
        """Give the external locations the file declares; none without a file."""
        return self._external_locations

    def secret_values(self) -> tuple[str, ...]:
        """Add the secrets of the external locations, which the logs mask as the others."""
        found = (*super().secret_values(), *self._external_locations.secrets())
        return tuple(dict.fromkeys(value for value in found if value))


# A ratio of the thresholds of the alerts: above zero, at most one (``Percent`` of the contract).
type Ratio = Annotated[Decimal, Field(gt=0, le=1)]


@dataclass(frozen=True, slots=True)
class OperatingParameters:
    """The operating parameters a process of the API reads, at their shipped values (§4.5.1).

    Set by the operator at the deployment (WF-ARC-0050), never by an operation; the status screen
    presents them (WF-ADM-0130). The three thresholds of the alerts are those the rules of
    Prometheus are written with (WF-OBS-0030), which the API receives to present them. The seventh,
    the largest avatar, is the installation's: the bootstrap writes it from its own setting
    (``InstallationSettings.avatar_max_bytes``), and the front reads it there without a session.
    """

    cache_validity_seconds: int = 600
    background_task_retention_days: int = 30
    task_queue_age_threshold_seconds: int = 900
    storage_usage_threshold: Decimal = Decimal("0.85")
    error_rate_threshold: Decimal = Decimal("0.05")
    error_rate_window_seconds: int = 300


class ApiSettings(ServiceSettings):
    """What the API reads besides: on how many processes it serves (US-2230), and its capacities.

    ``api_processes`` is the number of the processes of uvicorn that serve the requests, each with
    its own services and its own reserve of connections to the database: one by default, so that
    the tests and the workstation serve on the process that starts them.
    ``database_capacity_bytes`` and ``storage_capacity_bytes`` are the space the deployment gives
    PostgreSQL and the object storage, in bytes, of which the metrics say what is left
    (WF-OBS-0010): none by default, and then they say only what is used.
    ``tls_certificate`` and ``tls_key`` are the files of its certificate — followed by those up to
    the root — and of its key, in PEM (US-2840, TFX-02): given together, the API serves in TLS
    alone; neither, in HTTP, as on the workstation. ``metrics_port`` is a port of its own where it
    serves its metrics over HTTP, and nothing else (``getMetrics``, TFX-09): none by default, and
    then they are served on the port of the API alone.
    ``drain_file`` is the file whose presence says the instance is being stopped: from then on,
    each answer closes its connection (``waterfall.api.drain``, US-2850); none by default, as on
    the workstation, where nothing drains.
    ``prometheus_address`` is where it reaches the query API of Prometheus, for the status screen
    (TFX-14): in ``https://``, the certificate checked against ``tls_authority``, when an authority
    is given (US-2840); none by default, and then the screen says the metrics unavailable. The
    thresholds of the alerts are those the rules of Prometheus are written with, which it presents
    (``OperatingParameters``).
    """

    api_processes: int = Field(default=1, ge=1)
    database_capacity_bytes: int | None = Field(default=None, ge=1)
    storage_capacity_bytes: int | None = Field(default=None, ge=1)
    tls_certificate: Annotated[str | None, BeforeValidator(_none_when_empty)] = None
    tls_key: Annotated[str | None, BeforeValidator(_none_when_empty)] = None
    metrics_port: Annotated[
        Annotated[int, Field(ge=1, le=65535)] | None, BeforeValidator(_none_when_empty)
    ] = None
    drain_file: Annotated[str | None, BeforeValidator(_none_when_empty)] = None
    prometheus_address: Annotated[
        Annotated[str, Field(pattern="^https?://")] | None, BeforeValidator(_none_when_empty)
    ] = None
    task_queue_age_threshold_seconds: int = Field(default=900, ge=1)
    storage_usage_threshold: Ratio = Decimal("0.85")
    error_rate_threshold: Ratio = Decimal("0.05")
    error_rate_window_seconds: int = Field(default=300, ge=1)

    def transport_faults(self) -> list[str]:
        """Add Prometheus, when given, which must be reached in ``https://`` (TFX-14)."""
        address = self.prometheus_address
        encrypted = address is None or address.startswith("https://")
        return [
            *super().transport_faults(),
            *encrypted_fault("prometheus_address", encrypted=encrypted, wanted="be in https://"),
        ]

    def operating_parameters(self) -> OperatingParameters:
        """Give the operating parameters in force, as the environment sets them."""
        return OperatingParameters(
            cache_validity_seconds=self.indicators_cache_ttl,
            background_task_retention_days=self.background_task_retention_days,
            task_queue_age_threshold_seconds=self.task_queue_age_threshold_seconds,
            storage_usage_threshold=self.storage_usage_threshold,
            error_rate_threshold=self.error_rate_threshold,
            error_rate_window_seconds=self.error_rate_window_seconds,
        )

    @model_validator(mode="after")
    def _served(self) -> Self:
        if (self.tls_certificate is None) != (self.tls_key is None):
            message = f"{ENV_PREFIX}TLS_CERTIFICATE and {ENV_PREFIX}TLS_KEY go together"
            raise ValueError(message)
        if self.tls_certificate is not None and self.tls_key is not None:
            _served_pair(self.tls_certificate, self.tls_key)
        if self.metrics_port == self.port:
            message = f"{ENV_PREFIX}METRICS_PORT must not be {ENV_PREFIX}PORT"
            raise ValueError(message)
        return self


def _served_pair(certificate: str, key: str) -> None:
    """Refuse a certificate and a key the server could not serve, naming the variables."""
    for name, path in (("TLS_CERTIFICATE", certificate), ("TLS_KEY", key)):
        if not Path(path).is_file():
            message = f"{ENV_PREFIX}{name}: no file at {path}"
            raise ValueError(message)
    try:
        ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(certificate, key)
    except (OSError, ssl.SSLError) as error:
        message = (
            f"{ENV_PREFIX}TLS_CERTIFICATE and {ENV_PREFIX}TLS_KEY are not a certificate in PEM "
            "and its key, that can be read"
        )
        raise ValueError(message) from error


class ReserveSettings(PlatformSettings):
    """What the worker and the schedule both read: the size of the reserve of partitions (#4801).

    ``partition_reserve_size`` is how many sets of partitions the worker keeps made in advance for
    the projects to come, three by default, nought to inhibit the reserve (the filling then does
    nothing, the taking finds none and every creation makes its own partitions): a creation takes
    one with no DDL, and makes its own — waiting for a marking that runs — only when the reserve is
    empty (US-2830/L4). The worker fills
    the reserve up to it, and the schedule deposits the filling when the reserve holds fewer.
    """

    partition_reserve_size: int = Field(default=3, ge=0)


class ScheduleSettings(Settings, ReserveSettings):
    """What ``waterfall-worker schedule`` reads: the database and Redis, nothing else (TFX-10).

    ``purge_interval`` is how long the platform waits between two purges of what expired, ten
    minutes by default (EP-06, "La purge"). A task is deposited when the latest of its kind was
    submitted at least that long ago. The reading of the accounts and the backup are not here: an
    administrator sets when (``identity_sync_schedule``, ``backup_schedule``; US-3040, US-2910). The
    purge spares the latest task of each planned kind, however old, so that a schedule longer than
    the retention of the tasks does not make a task due again at each purge. Under Helm the first
    reading may leave before the realm of Keycloak is applied (a hook after the installation): it
    then fails and the next is due at the next occurrence of its schedule.
    ``restore_test_job`` is the file of the Job of the test of a restoration, which the chart
    mounts: under Kubernetes the schedule makes it in its namespace every ``restore_test_interval``
    seconds, thirty days; none, the default, plans no test: under Compose a planned task of the
    host runs it (US-2930).
    """

    purge_interval: int = Field(default=600, ge=1)
    restore_test_job: str | None = Field(default=None, min_length=1)
    restore_test_interval: int = Field(default=2_592_000, ge=1)


class WorkerSettings(ServiceSettings, ReserveSettings):
    """What the worker reads besides: the two databases a backup dumps, as the role of the backup.

    ``metrics_port`` is where it serves its metrics, on the address of ``host`` (WF-OBS-0010).
    The purge it runs keeps the history of a session ``undo_retention_hours`` hours, twelve by
    default: the longest session of the realm (EP-06, "L'historique annulable et le collage"); and
    a task ended ``background_task_retention_days`` days, the operating parameter of the same name
    (``ServiceSettings``).
    A task of a kind it does not run waits ``unknown_kind_wait_seconds`` seconds, an hour by
    default, for a worker that does — during a rolling update —, counted from its submission, then
    fails (#809).
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
    unknown_kind_wait_seconds: int = Field(default=3600, ge=1)


# The largest avatar a new installation accepts, as the specification ships it (§4.4.1).
SHIPPED_AVATAR_MAX_BYTES = 512 * 1024


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
    does not know. ``avatar_max_bytes`` is the largest avatar, an operating parameter (§4.4.1),
    shipped at 512 KB and never above 8 MiB, which every run writes in the installation (#3965). It
    deposits no task and serves nothing: it reads neither Redis nor where the API listens.
    """

    installation_client_secret: SecretStr = Field(min_length=1)
    admin_email: str = Field(min_length=1)
    default_language: Literal["fr", "en"]
    currency: str = Field(pattern="^[A-Z]{3}$")
    company_name: str = Field(min_length=1, max_length=200, pattern=r"\S")
    time_zone: Annotated[
        str | None, BeforeValidator(_none_when_empty), AfterValidator(_known_time_zone_if_given)
    ] = None
    avatar_max_bytes: int = Field(default=SHIPPED_AVATAR_MAX_BYTES, ge=1, le=8 * 1024**2)


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


class RestoreTestSettings(StorageSettings, RealmSettings):
    """What the test of a restoration reads, ``waterfall-restore test`` (WF-EXP-0060, US-2930).

    ``database_url`` designates the database of Waterfall of the production, as the role of the
    service, which reads the backups and inscribes the test; the storage, its bucket of the backups.
    ``restore_test_database_url`` and ``restore_test_keycloak_database_url`` designate the two
    databases of the ephemeral platform, as their owners, which the test replaces by the backup;
    ``restore_test_api_address`` the API of that platform, whose readiness says it started, checked
    against the roots of ``restore_test_authority``, or of ``tls_authority`` if none is given.
    ``restore_test_restored_file`` is the file the test writes once the databases are restored,
    which the platform waits for to start, and ``restore_test_patience`` how long, in seconds, it is
    given to start then: thirty minutes by default. ``keycloak_realm`` is the realm whose accounts
    are counted, that of the installation.
    """

    restore_test_database_url: SecretStr = Field(min_length=1)
    restore_test_keycloak_database_url: SecretStr = Field(min_length=1)
    restore_test_api_address: str = Field(min_length=1, pattern="^https?://")
    restore_test_authority: Roots = None
    restore_test_restored_file: str = Field(min_length=1)
    restore_test_patience: int = Field(default=1800, ge=1)

    def transport_faults(self) -> list[str]:
        """Add the API of the ephemeral platform, which must be reached in ``https://``."""
        encrypted = self.restore_test_api_address.startswith("https://")
        return [
            *super().transport_faults(),
            *encrypted_fault(
                "restore_test_api_address", encrypted=encrypted, wanted="be in https://"
            ),
        ]


class ComponentsSettings(Settings, KeycloakSettings):
    """What the check of the components reads, ``waterfall-check-components`` (WF-CMP-0020-A).

    ``database_url`` and ``redis_url`` designate the PostgreSQL and the Redis to check; Keycloak is
    reached as the service does, by its address, its realm and the secret of the service account,
    which the extension answers with its version (#4641). It opens no database of its own and
    serves nothing.
    """


class WitnessSettings(PlatformSettings):
    """What the loader of the witness reads, ``waterfall-api load-witness`` (WF-QUA-0040, EP-05).

    ``database_url`` designates the role of the service: the loader writes through the interfaces
    of the modules, as the service does, never as the owner of the tables. ``witness_path`` is the
    directory of the description of the witness, the examples of the contract (``fixtures/api``).
    It reaches neither Redis nor Keycloak.
    """

    witness_path: str = Field(min_length=1)


class ReferenceBackupSettings(WitnessSettings, Settings, StorageSettings):
    """What ``waterfall-api backup-reference`` reads (US-2950, #4114).

    The role of the service, as the loader of the witness, to check the set and deposit its backup
    as the schedule does; Redis, to put it in the queue; the bucket of the backups, to read its
    archive back once the worker has taken it.
    """


class ReferenceRestoreSettings(PlatformSettings):
    """What ``waterfall-api restore-reference`` reads (US-2950, #4114).

    The owners of the two databases of a fresh platform, as the service of the restoration reaches
    them (``RestoreSettings``): ``database_url`` Waterfall's, ``keycloak_database_url`` the identity
    provider's. Nothing else: it reads an archive from a file, and starts nothing.
    """

    keycloak_database_url: SecretStr = Field(min_length=1)


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


def load_restore_test_settings() -> RestoreTestSettings:
    """Read the settings of the test of a restoration, as ``load_settings`` does."""
    return _load(RestoreTestSettings)


def load_installation_settings() -> InstallationSettings:
    """Read the settings of the bootstrap, as ``load_settings`` does."""
    return _load(InstallationSettings)


def load_components_settings() -> ComponentsSettings:
    """Read the settings of the check of the components, as ``load_settings`` does."""
    return _load(ComponentsSettings)


def load_witness_settings() -> WitnessSettings:
    """Read the settings of the loader of the witness, as ``load_settings`` does."""
    return _load(WitnessSettings)


def load_reference_backup_settings() -> ReferenceBackupSettings:
    """Read the settings of the backup of the reference set, as ``load_settings`` does."""
    return _load(ReferenceBackupSettings)


def load_reference_restore_settings() -> ReferenceRestoreSettings:
    """Read the settings of the restoration of the reference set, as ``load_settings`` does."""
    return _load(ReferenceRestoreSettings)


def _named(location: tuple[int | str, ...]) -> str:
    """Name the variable of a fault; a fault between several settings names them itself."""
    if not location:
        return ""
    return f"{ENV_PREFIX}{'_'.join(str(part) for part in location).upper()}: "


def _load[Kind: PlatformSettings](kind: type[Kind]) -> Kind:
    # The values come from the environment, which pydantic-settings reads itself.
    from_environment: dict[str, Any] = {}
    try:
        return kind(**from_environment)
    except ValidationError as error:
        faults = [
            _named(fault["loc"]) + ("is missing" if fault["type"] == "missing" else fault["msg"])
            for fault in error.errors(include_input=False, include_url=False)
        ]
        message = "settings are not valid: " + "; ".join(faults)
        raise SettingsError(message) from None
