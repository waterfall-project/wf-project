# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Settings and secrets, read from the environment at start (WF-SEC-0010).

A secret that is missing stops the process and names the variable that lacks, rather than
letting the service start without it. The secrets are ``SecretStr``: printing the settings
shows no value.
"""

from typing import Any

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "WATERFALL_"


class SettingsError(Exception):
    """The environment does not give the settings the service needs."""


class Settings(BaseSettings):
    """What a service of the platform reads from its environment."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    database_url: SecretStr = Field(min_length=1)
    redis_url: SecretStr = Field(min_length=1)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")


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
