# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The image the end-to-end paths run in carries the Playwright the front locks (#492, #498).

The paths run in Playwright's image, whose browser is the one its version expects
(`.github/workflows/e2e.yml`). Raising `@playwright/test` in the lock file without raising the
image would stop every path on a browser it cannot find, in the merge queue: this test fails
first, on the pull request that forgets one side. The image is pinned by digest, the tag saying
which version the digest stands for.
"""

import re

from wftools import REPOSITORY

WORKFLOW = REPOSITORY / ".github/workflows/e2e.yml"
LOCK = REPOSITORY / "frontend/pnpm-lock.yaml"

IMAGE = re.compile(
    r"^\s+image: mcr\.microsoft\.com/playwright:(?P<tag>[^@\s]+)(?:@(?P<digest>\S+))?\s*$",
    re.MULTILINE,
)
# The version the front's importer resolves, not a specifier: `version:` under its entry.
LOCKED = re.compile(
    r"^      '@playwright/test':\n        specifier: \S+\n        version: (?P<version>\S+)$",
    re.MULTILINE,
)
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def image(workflow: str) -> tuple[str, str | None]:
    """Return the tag and the digest of the Playwright image a workflow runs in."""
    found = IMAGE.findall(workflow)
    assert len(found) == 1, f"one Playwright image expected in {WORKFLOW.name}: {found}"
    tag, digest = found[0]
    return tag, digest or None


def locked(lock: str) -> str:
    """Return the version of @playwright/test the lock file resolves."""
    found = LOCKED.findall(lock)
    assert len(found) == 1, f"one @playwright/test expected in {LOCK.name}: {found}"
    return found[0]


def test_the_image_of_the_paths_is_the_playwright_the_front_locks() -> None:
    tag, _ = image(WORKFLOW.read_text(encoding="utf-8"))
    assert tag == f"v{locked(LOCK.read_text(encoding='utf-8'))}-noble"


def test_the_image_of_the_paths_is_pinned_by_its_digest() -> None:
    _, digest = image(WORKFLOW.read_text(encoding="utf-8"))
    assert digest is not None
    assert DIGEST.fullmatch(digest)


def test_an_image_of_another_version_is_told_apart() -> None:
    workflow = "    image: mcr.microsoft.com/playwright:v1.62.0-noble@sha256:" + "0" * 64 + "\n"
    lock = "      '@playwright/test':\n        specifier: ^1.63.0\n        version: 1.63.0\n"
    assert image(workflow)[0] != f"v{locked(lock)}-noble"


def test_an_image_without_digest_is_told_apart() -> None:
    assert image("    image: mcr.microsoft.com/playwright:v1.63.0-noble\n") == (
        "v1.63.0-noble",
        None,
    )
