# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The data of the environments of development and of integration: engendered, never real.

(WF-EXP-0010-A, US-2960.) Two things are held here, on the files of the repository: the sets the
repository engenders — the fixtures, the witness and the volumes among them — name no address but
in a domain reserved to the tests; and the platforms of development and of integration take their
data from the repository alone. That the witness and the reference set loaded hold no address but
in ``waterfall.test`` is held by the tests of the back (``test_witness_reference.py``), and that a
copy of the production is anonymised before it is opened by ``test_anonymization.py``.
"""

import re
from typing import TYPE_CHECKING, Any, cast

import pytest
import yaml

from wftools import REPOSITORY

if TYPE_CHECKING:
    from pathlib import Path

FIXTURES = REPOSITORY / "fixtures"
COMPOSE = REPOSITORY / "deploy" / "compose"
# The domain reserved to the tests (RFC 6761), that every engendered address bears.
RESERVED = "waterfall.test"
# The examples of the contract bear the domain RFC 2606 reserves to examples: the contract is
# frozen, and the loader of the witness gives each of them the domain of the tests
# (witness/projects.py).
CONTRACT_EXAMPLES = FIXTURES / "api"
EXAMPLES = "example.com"
ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})")
# The platforms of development and of integration: the fake back of the screens, the service
# platform the parcours and the tests of Keycloak run on, the services of the tests of the back.
ENVIRONMENTS = ("compose.dev.yaml", "compose.service.yaml", "compose.test.yaml")
# The one service that writes data on them, and what it writes from.
LOADER = ("witness", ["waterfall-api", "load-witness"])


def foreign_addresses(text: str, allowed: tuple[str, ...]) -> list[str]:
    """Give the addresses of a text whose domain is none of those allowed, nor under one of them."""
    return [
        found.group(0)
        for found in ADDRESS.finditer(text)
        if not any(
            found.group(1).lower() == domain or found.group(1).lower().endswith(f".{domain}")
            for domain in allowed
        )
    ]


def _allowed(path: Path) -> tuple[str, ...]:
    if path.is_relative_to(CONTRACT_EXAMPLES):
        return (RESERVED, EXAMPLES)
    return (RESERVED,)


def _texts() -> list[tuple[Path, str]]:
    """Give every file of the fixtures that reads as text, with its text; a binary passed over."""
    texts: list[tuple[Path, str]] = []
    for path in sorted(FIXTURES.rglob("*")):
        if not path.is_file():
            continue
        try:
            texts.append((path, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return texts


@pytest.mark.requirement("WF-EXP-0010-A")
def test_the_engendered_sets_bear_no_address_but_in_the_reserved_domain() -> None:
    # « Aucun environnement hors production ne contient une adresse électronique réelle, hors
    # l'environnement isolé du test de restauration. » : the fixtures, the witness and its volumes
    # included, name no address but in waterfall.test — the examples of the contract in
    # example.com, which the loader of the witness gives waterfall.test.
    texts = _texts()
    assert len(texts) > 100
    assert sum(len(ADDRESS.findall(text)) for _, text in texts) > 0
    foreign = {
        str(path.relative_to(REPOSITORY)): found
        for path, text in texts
        if (found := foreign_addresses(text, _allowed(path)))
    }
    assert foreign == {}


@pytest.mark.story("US-2960")
def test_an_address_outside_the_reserved_domains_is_found() -> None:
    # Proper to US-2960: the check above finds a real address, wherever it lies in a text, and
    # passes over a domain reserved, or one under it.
    text = (
        '{"to": "jeanne.dupont@entreprise.fr", "a": "a@waterfall.test", "b": "c@x.waterfall.test"}'
    )
    assert foreign_addresses(text, (RESERVED,)) == ["jeanne.dupont@entreprise.fr"]
    assert foreign_addresses("contact@example.com", (RESERVED,)) == ["contact@example.com"]
    assert foreign_addresses("contact@example.com", (RESERVED, EXAMPLES)) == []
    assert foreign_addresses("@types/node and user@localhost", (RESERVED,)) == []


def _services(name: str) -> dict[str, Any]:
    """Give the services of a file of Compose, by name."""
    document = yaml.safe_load((COMPOSE / name).read_text(encoding="utf-8"))
    return document["services"]


def _volumes(service: dict[str, Any]) -> list[Any]:
    return list(service.get("volumes") or [])


def _source(volume: Any) -> str:
    """Give the source of a volume, written short or long."""
    if isinstance(volume, str):
        return volume.split(":")[0]
    return str(cast("dict[str, Any]", volume)["source"])


def _bind_sources(service: dict[str, Any]) -> list[str]:
    """Give the paths of the host a service mounts; a volume of Docker is none.

    A volume is written short, ``source:target[:mode]``, or long, its source under a key.
    """
    sources: list[str] = []
    for volume in _volumes(service):
        source = _source(volume)
        if source.startswith((".", "/", "~", "$")):
            sources.append(source)
    return sources


@pytest.mark.requirement("WF-EXP-0010-A")
@pytest.mark.parametrize("name", ENVIRONMENTS)
def test_the_platforms_of_development_and_integration_take_their_data_from_the_repository(
    name: str,
) -> None:
    # « Le jeu de données des environnements de développement et d'intégration est engendré par un
    # outil du dépôt, sans copie de production. » : no service of these platforms mounts a path of
    # the host outside the repository, from which a copy could come.
    for service_name, service in _services(name).items():
        for source in _bind_sources(service):
            assert not source.startswith(("/", "~", "$")), (service_name, source)
            assert (COMPOSE / source).resolve().is_relative_to(REPOSITORY), (service_name, source)


@pytest.mark.requirement("WF-EXP-0010-A")
def test_the_service_platform_writes_its_data_by_the_loader_of_the_repository() -> None:
    # « Le jeu de données des environnements de développement et d'intégration est engendré par un
    # outil du dépôt, sans copie de production. » : the one service that writes a data set on the
    # service platform is the loader of the witness, from the fixtures of the repository, read
    # only.
    name, command = LOADER
    loader = _services("compose.service.yaml")[name]
    assert loader["command"] == command
    sources = _bind_sources(loader)
    assert sources
    for source in sources:
        assert (COMPOSE / source).resolve().is_relative_to(FIXTURES), source
    assert all(str(volume).endswith(":ro") for volume in _volumes(loader))
