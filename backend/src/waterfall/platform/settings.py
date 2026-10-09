# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Settings and secrets, read from the environment at start (WF-SEC-0010).

A secret that is missing stops the process and names the variable that lacks, rather than
letting the service start without it. The secrets are ``SecretStr``: printing the settings
shows no value.
"""

from contextlib import suppress
from typing import Any
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
    more. A decoded form shorter than ``MIN_DECODED_LENGTH`` characters is not kept: it would
    hide every text that contains it.
    """
    rest = value.partition("://")[2]
    passwords = [rest[:index].partition(":")[2] for index, char in enumerate(rest) if char == "@"]
    with suppress(ValueError):
        passwords.append(urlsplit(value).password or "")
    found: list[str] = []
    for password in dict.fromkeys(passwords):
        if not password:
            continue
        decoded = [unquote(password), unquote_plus(password)]
        found += [password, *(text for text in decoded if len(text) >= MIN_DECODED_LENGTH)]
    return found


class Settings(BaseSettings):
    """What a service of the platform reads from its environment."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    database_url: SecretStr = Field(min_length=1)
    redis_url: SecretStr = Field(min_length=1)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    def secret_values(self) -> tuple[str, ...]:
        """Give every secret held, and the password a URL secret carries, for the logs to mask.

        A driver quotes the password alone as readily as the address: both are secrets.
        """
        values = (getattr(self, name) for name in type(self).model_fields)
        held = [value.get_secret_value() for value in values if isinstance(value, SecretStr)]
        extra = [part for value in held for part in _url_secrets(value)]
        return tuple(dict.fromkeys(value for value in [*held, *extra] if value))


def load_settings() -> Settings:
    """Read the settings from the environment, or raise a ``SettingsError`` that names each fault.

    The message names the variables and what is wrong with them, never the values they hold.
    """
    # The values come from the environment, which pydantic-settings reads itself.
    from_environment: dict[str, Any] = {}
    try:
        return Settings(**from_environment)
    except ValidationError as error:
        faults = [
            f"{ENV_PREFIX}{'_'.join(str(part) for part in fault['loc']).upper()}: "
            + ("is missing" if fault["type"] == "missing" else fault["msg"])
            for fault in error.errors(include_input=False, include_url=False)
        ]
        message = "settings are not valid: " + "; ".join(faults)
        raise SettingsError(message) from None
