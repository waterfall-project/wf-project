# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The images of the platform: the PostgreSQL of the tests is the PostgreSQL of the service."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = re.compile(r"image:\s*(postgres:\S+@sha256:[0-9a-f]{64})\s*$", re.MULTILINE)


def postgres_images(path: Path) -> list[str]:
    """List the PostgreSQL images, pinned by their digest, that a file names."""
    return IMAGE.findall(path.read_text(encoding="utf-8"))


def test_the_postgresql_of_the_chain_is_the_image_of_the_service_platform() -> None:
    chain = postgres_images(ROOT / ".github" / "workflows" / "back.yml")
    platform = postgres_images(ROOT / "deploy" / "compose" / "compose.service.yaml")
    assert len(chain) == 1
    assert chain == platform
