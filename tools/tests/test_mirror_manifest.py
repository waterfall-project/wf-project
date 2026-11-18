# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The manifest of the images of Docker Hub, which Dependabot reads, and its copy into the files.

Dependabot does not read a reference behind the prefix of the mirror (``FROM ${WATERFALL_MIRROR}…``,
``${WATERFALL_MIRROR:-}…``): its watch of the images found nothing from the mirror on (#3025). It
follows ``deploy/images/Dockerfile`` instead, one bare line per image; a raise changes that file
alone, and the chain of its pull request fails here until the files follow it (US-2490).
"""

from typing import TYPE_CHECKING

import pytest

from wftools import mirror

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.story("US-2490")

OLD = "sha256:" + "a" * 64
NEW = "sha256:" + "b" * 64
OTHER = "sha256:" + "c" * 64


def manifest(root: Path, *lines: str) -> None:
    """Write the manifest of a directory standing for the repository."""
    path = root / mirror.MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"FROM {line}\n" for line in lines)
    path.write_text(f"# The manifest.\n{body}", encoding="utf-8")


def write(root: Path, name: str, text: str) -> Path:
    """Write a file of a directory standing for the repository."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# Every form a reference of Docker Hub takes in the repository, at the old digest.
DOCKERFILE = f"ARG WATERFALL_MIRROR=\nFROM ${{WATERFALL_MIRROR}}python:3.14@{OLD} AS python\n"
COMPOSE = (
    f"x-postgres-image: &postgres-image ${{WATERFALL_MIRROR:-}}postgres:18@{OLD}\n"
    "services:\n"
    "  db:\n"
    "    image: *postgres-image\n"
    "  cache:\n"
    f"    image: ${{WATERFALL_MIRROR:-}}redis:8@{OLD}\n"
    "  front-end:\n"
    f"    image: caddy:2.11.7-alpine@{OLD}\n"
)
WORKFLOW = (
    "jobs:\n"
    "  tests:\n"
    "    services:\n"
    "      redis:\n"
    f"        image: {mirror.MIRROR}/redis:8@{OLD}\n"
    "    steps:\n"
    "      - run: >-\n"
    f"          docker run --detach {mirror.MIRROR}/dxflrs/garage:v2@{OLD}\n"
)
# What is not an image of Docker Hub, and stays as it is.
ELSEWHERE = (
    f"FROM mcr.microsoft.com/playwright:v1.64.1-noble@{OTHER} AS work\n"
    f"FROM ghcr.io/astral-sh/uv:0.13.8@{OTHER} AS uv\n"
    f"ADD --checksum={OTHER} https://example.org/a.tar.gz /a.tar.gz\n"
    "FROM ${WATERFALL_MIRROR}node:26-alpine\n"
)
RAISED = (
    f"python:3.14@{NEW}",
    f"postgres:18@{NEW}",
    f"redis:8@{NEW}",
    f"caddy:2.11.9-alpine@{NEW}",
    f"dxflrs/garage:v2@{NEW}",
)


def repository(root: Path) -> Path:
    """Write every form of reference at the old digest, and a manifest that raised them all."""
    manifest(root, *RAISED)
    write(root, "backend/Dockerfile", DOCKERFILE)
    write(root, "deploy/compose/compose.prod.yaml", COMPOSE)
    write(root, ".github/workflows/back.yml", WORKFLOW)
    return write(root, "deploy/e2e/Dockerfile", ELSEWHERE)


def test_the_files_follow_the_manifest_and_it_names_no_image_they_do_not_use() -> None:
    message = mirror.drifted()
    assert message is None, message


def test_the_manifest_names_each_image_of_the_mirror_once_bare() -> None:
    images, wrong = mirror.manifest()
    assert wrong == []
    assert set(images) == {image.path for image in mirror.referenced()}


def test_every_form_of_reference_is_read_and_compared_with_the_manifest(tmp_path: Path) -> None:
    repository(tmp_path)
    wrong = mirror.drift(tmp_path)
    # Each reference of Docker Hub, prefixed or bare, in a Dockerfile, a Compose file, an anchor,
    # the service or the step of a workflow; none of the other registries' nor without a digest.
    assert len(wrong) == 6
    assert all(f"where {mirror.MANIFEST} has" in line for line in wrong)
    assert any(line.startswith("backend/Dockerfile:2: python:3.14@") for line in wrong)
    compose = "deploy/compose/compose.prod.yaml"
    assert any(line.startswith(f"{compose}:1: postgres:18@") for line in wrong)
    assert any(line.startswith(f"{compose}:8: caddy:") for line in wrong)
    assert any(line.startswith(".github/workflows/back.yml:8: dxflrs/garage") for line in wrong)
    assert not any("deploy/e2e" in line for line in wrong)


def test_a_drift_names_the_two_gestures_of_a_raise(tmp_path: Path) -> None:
    repository(tmp_path)
    message = mirror.drifted(tmp_path)
    assert message is not None
    assert "make mirror-sync" in message
    assert "make mirror PUSH=yes" in message


def test_a_tag_that_differs_alone_is_a_drift(tmp_path: Path) -> None:
    manifest(tmp_path, f"redis:8.2@{OLD}")
    write(tmp_path, "deploy/compose/compose.test.yaml", f"    image: redis:8@{OLD}\n")
    said = f"deploy/compose/compose.test.yaml:1: redis:8@{OLD}, where {mirror.MANIFEST} has"
    assert mirror.drift(tmp_path) == [f"{said} redis:8.2@{OLD}"]


def test_an_image_the_manifest_does_not_name_and_one_nothing_uses_are_said(tmp_path: Path) -> None:
    manifest(tmp_path, f"redis:8@{OLD}")
    write(tmp_path, "deploy/compose/compose.test.yaml", f"    image: postgres:18@{OLD}\n")
    assert mirror.drift(tmp_path) == [
        f"deploy/compose/compose.test.yaml:1: postgres:18@{OLD} is not in {mirror.MANIFEST}",
        f"{mirror.MANIFEST}: redis:8@{OLD} is used by no file",
    ]


def test_a_line_of_the_manifest_with_a_prefix_or_twice_is_said(tmp_path: Path) -> None:
    manifest(tmp_path, f"${{WATERFALL_MIRROR}}redis:8@{OLD}", f"node:26@{OLD}", f"node:25@{OLD}")
    write(tmp_path, "deploy/compose/mock.Dockerfile", f"FROM node:26@{OLD}\n")
    wrong = mirror.drift(tmp_path)
    assert wrong[0].startswith(f"{mirror.MANIFEST}: FROM ${{WATERFALL_MIRROR}}redis:8")
    assert wrong[1] == f"{mirror.MANIFEST}: node is named twice"
    assert len(wrong) == 2


def test_a_missing_manifest_is_said(tmp_path: Path) -> None:
    assert mirror.drift(tmp_path) == [f"{mirror.MANIFEST} is missing"]


def test_sync_copies_the_manifest_into_every_form_and_keeps_the_prefix(tmp_path: Path) -> None:
    elsewhere = repository(tmp_path)
    changed = mirror.sync(tmp_path)
    assert {path.relative_to(tmp_path).as_posix() for path in changed} == {
        "backend/Dockerfile",
        "deploy/compose/compose.prod.yaml",
        ".github/workflows/back.yml",
    }
    assert mirror.drift(tmp_path) == []
    dockerfile = (tmp_path / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert dockerfile == DOCKERFILE.replace(OLD, NEW)
    compose = (tmp_path / "deploy" / "compose" / "compose.prod.yaml").read_text(encoding="utf-8")
    assert compose == COMPOSE.replace(OLD, NEW).replace("caddy:2.11.7", "caddy:2.11.9")
    workflow = (tmp_path / ".github" / "workflows" / "back.yml").read_text(encoding="utf-8")
    assert workflow == WORKFLOW.replace(OLD, NEW)
    assert elsewhere.read_text(encoding="utf-8") == ELSEWHERE


def test_sync_run_again_changes_nothing(tmp_path: Path) -> None:
    repository(tmp_path)
    mirror.sync(tmp_path)
    files = sorted(path for path in tmp_path.rglob("*") if path.is_file())
    before = {path: path.read_text(encoding="utf-8") for path in files}
    assert mirror.sync(tmp_path) == []
    assert {path: path.read_text(encoding="utf-8") for path in files} == before


def test_sync_leaves_an_image_the_manifest_does_not_name(tmp_path: Path) -> None:
    manifest(tmp_path, f"redis:8@{NEW}")
    text = f"    image: postgres:18@{OLD}\n    image: redis:8@{OLD}\n"
    path = write(tmp_path, "deploy/compose/compose.test.yaml", text)
    assert mirror.sync(tmp_path) == [path]
    assert path.read_text(encoding="utf-8") == text.replace(f"redis:8@{OLD}", f"redis:8@{NEW}")


def test_main_sync_says_the_files_it_changed_and_fails_on_what_remains(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository(tmp_path)
    assert mirror.main(["sync"], root=tmp_path) == 0
    said = capsys.readouterr().err
    assert f"backend/Dockerfile follows {mirror.MANIFEST}" in said
    write(tmp_path, "deploy/compose/compose.test.yaml", f"    image: mailpit:1@{OLD}\n")
    assert mirror.main(["sync"], root=tmp_path) == 1
    assert f"mailpit:1@{OLD} is not in {mirror.MANIFEST}" in capsys.readouterr().err


def test_sync_refuses_push(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repository(tmp_path)
    with pytest.raises(SystemExit) as stop:
        mirror.main(["sync", "--push"], root=tmp_path)
    assert stop.value.code == 2
    assert "--push does not go with sync" in capsys.readouterr().err
