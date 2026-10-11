# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The images of the platform: the PostgreSQL and the Redis of the tests are the service's."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
IMAGE = re.compile(r"image:\s*(postgres:\S+@sha256:[0-9a-f]{64})\s*$", re.MULTILINE)


def postgres_images(path: Path) -> list[str]:
    """List the PostgreSQL images, pinned by their digest, that a file names."""
    return IMAGE.findall(path.read_text(encoding="utf-8"))


def test_the_postgresql_of_the_chain_is_the_image_of_the_service_platform() -> None:
    chain = postgres_images(ROOT / ".github" / "workflows" / "back.yml")
    # The server, the service that creates the database of Keycloak on it, and the one that lets
    # the role of the service sign in.
    platform = postgres_images(ROOT / "deploy" / "compose" / "compose.service.yaml")
    assert len(chain) == 1
    assert platform == chain * 3


def test_the_redis_of_the_chain_is_the_image_of_the_service_platform() -> None:
    redis = re.compile(r"image:\s*(redis:\S+@sha256:[0-9a-f]{64})\s*$", re.MULTILINE)
    workflows = ROOT / ".github" / "workflows"
    compose = ROOT / "deploy" / "compose" / "compose.service.yaml"
    platform = redis.findall(compose.read_text(encoding="utf-8"))
    for chain in ("back.yml", "front.yml"):
        assert redis.findall((workflows / chain).read_text(encoding="utf-8")) == platform


def test_redis_runs_as_its_own_user_and_its_command_does_not_carry_the_secret() -> None:
    compose = yaml.safe_load(
        (ROOT / "deploy" / "compose" / "compose.service.yaml").read_text(encoding="utf-8")
    )
    redis = compose["services"]["redis"]
    assert redis["user"] == "redis"
    command = " ".join(redis["command"])
    assert "$$REDISCLI_AUTH" in command
    assert "${WATERFALL_REDIS_PASSWORD" not in command
