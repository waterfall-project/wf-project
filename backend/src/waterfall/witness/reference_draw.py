# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference of the reference set (WF-QUA-0040; US-2950): what a seed draws beside the witness.

The set starts from the witness and prolongs it to the volumes of table 13 (§4.6.2): forty nodes of
the organisation, a hundred and fifty roles of resources, two hundred categories of cost, fifteen
years of hourly rates and five hundred accounts. The witness holds the categories and the fifteen
years of its grid already; the draw adds the nodes, the roles and the accounts it lacks, counted
from its description, so that the platform holds the volumes and no more.

Everything is drawn from the seed alone (``Draw``), object by object — never from what the platform
holds, nor from the order of a run: two engenderings give the same identifiers, codes, labels and
names, and an object drawn does not depend on how many others are. The identifiers are derived from
the seed, the kind of the object and its number (``identifier``). Every name is fictitious, every
address in the domain reserved to the tests (``waterfall.test``, WF-QUA-0040, WF-EXP-0010).

Nothing here reads or writes the base: ``reference_load`` writes what this draws, through the
interfaces of the modules.
"""

import hashlib
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from itertools import count
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from waterfall.witness.projects import WITNESS_DOMAIN

if TYPE_CHECKING:
    from collections.abc import Sequence

# The seed of the reference set: fixed, so that the set is always the same (WF-QUA-0040).
SEED = 2950
# The volumes of table 13 (§4.6.2) the reference set holds, the witness's objects counted; the
# projects are those "in the portfolio", in progress and in pricing.
NODES, ROLES, CATEGORIES, RATE_YEARS, ACCOUNTS, PROJECTS = 40, 150, 200, 15, 500, 300
# The directions the drawn nodes are under, each a root of its own; the others are their services.
DIRECTIONS = ("Nord", "Sud", "Est", "Ouest")
_NAMESPACE = uuid5(NAMESPACE_URL, "https://waterfall.example/reference")

SERVICES = (
    "Bureau d'études mécanique",
    "Bureau d'études électricité",
    "Atelier de fabrication",
    "Atelier de montage",
    "Service essais",
    "Service méthodes",
    "Service installation",
    "Service qualité",
)
TRADES = (
    "Ingénieur méthodes",
    "Ingénieur d'études",
    "Chef de chantier",
    "Technicien d'essais",
    "Technicien de maintenance",
    "Dessinateur projeteur",
    "Monteur câbleur",
    "Soudeur",
    "Chaudronnier",
    "Automaticien",
    "Metteur en service",
    "Contrôleur qualité",
)
# The names of the accounts: first names, and plants for last names, which name no one.
FIRST_NAMES = (
    "Alix",
    "Andréa",
    "Ange",
    "Ariel",
    "Aubin",
    "Bastien",
    "Bérénice",
    "Céleste",
    "Clément",
    "Colombe",
    "Cyprien",
    "Daphné",
    "Eloi",
    "Elsa",
    "Fabien",
    "Flore",
    "Gaspard",
    "Hélène",
    "Inès",
    "Jules",
)
LAST_NAMES = (
    "Aubépine",
    "Bourrache",
    "Capucine",
    "Cerfeuil",
    "Chicorée",
    "Coriandre",
    "Cresson",
    "Escarole",
    "Fenouil",
    "Garance",
    "Genièvre",
    "Glycine",
    "Houblon",
    "Lavande",
    "Livèche",
    "Marjolaine",
    "Mélisse",
    "Moutarde",
    "Myrtille",
    "Oseille",
)


def identifier(kind: str, *parts: object) -> UUID:
    """Give the identifier of an object of the set: derived from the seed, its kind and its rank."""
    return uuid5(_NAMESPACE, "/".join((str(SEED), kind, *(str(part) for part in parts))))


class Draw:
    """The numbers the seed draws for one object, one after the other.

    Each is read from the SHA-256 of the seed, the object and its rank among the numbers drawn for
    it: the same on every platform and under every version of Python, which a generator of the
    standard library does not promise across versions.
    """

    def __init__(self, kind: str, *parts: object) -> None:
        self._key = "/".join((str(SEED), kind, *(str(part) for part in parts)))
        self._ranks = count(1)

    def below(self, bound: int) -> int:
        """Draw a whole number from nought to ``bound``, excluded."""
        digest = hashlib.sha256(f"{self._key}/{next(self._ranks)}".encode()).digest()
        return int.from_bytes(digest[:8]) % bound

    def between(self, low: int, high: int) -> int:
        """Draw a whole number from ``low`` to ``high``, both included."""
        return low + self.below(high - low + 1)

    def choice[Item](self, items: Sequence[Item]) -> Item:
        """Draw one of the items."""
        return items[self.below(len(items))]


@dataclass(frozen=True, slots=True)
class Base:
    """What the witness gives the draw: its objects the drawn ones attach to, and its counts.

    ``rated`` are the categories of labour the witness rates on each year of its grid: a role is
    attached to one of them, so that no line of a project lacks a rate. ``calendars``, its active
    calendars; ``nodes``, ``roles``, ``accounts`` and ``projects``, how many it holds, and
    ``portfolio``, how many of its projects are in the portfolio — in pricing or in progress.
    """

    rated: tuple[UUID, ...]
    non_labour: tuple[UUID, ...]
    provision: UUID
    calendars: tuple[UUID, ...]
    nodes: int
    roles: int
    accounts: int
    projects: int
    portfolio: int


@dataclass(frozen=True, slots=True)
class DrawnNode:
    """A node drawn: a direction, a root, or one of its services."""

    node_id: UUID
    code: str
    label: str
    parent_id: UUID | None


@dataclass(frozen=True, slots=True)
class DrawnRole:
    """A role drawn, under a service, attached to a rated category of labour and a calendar."""

    role_id: UUID
    code: str
    label: str
    node_id: UUID
    category_id: UUID
    calendar_id: UUID
    headcount: Decimal


@dataclass(frozen=True, slots=True)
class DrawnAccount:
    """A local account drawn, attached to a service, its address in ``waterfall.test``."""

    user_id: UUID
    last_name: str
    first_name: str
    email: str
    node_id: UUID


@dataclass(frozen=True, slots=True)
class Reference:
    """The nodes, the roles and the accounts the reference set adds to the witness's."""

    nodes: tuple[DrawnNode, ...]
    roles: tuple[DrawnRole, ...]
    accounts: tuple[DrawnAccount, ...]


def draw_reference(base: Base) -> Reference:
    """Draw what the witness lacks of the reference of table 13, from the seed alone."""
    nodes = _nodes(NODES - base.nodes)
    services = tuple(node.node_id for node in nodes if node.parent_id is not None)
    roles = tuple(_role(number, base, services) for number in range(1, ROLES - base.roles + 1))
    accounts = tuple(
        _account(number, services) for number in range(1, ACCOUNTS - base.accounts + 1)
    )
    return Reference(nodes, roles, accounts)


def _nodes(wanted: int) -> tuple[DrawnNode, ...]:
    """Draw the directions, then their services in turn, ``wanted`` nodes in all."""
    directions = tuple(
        DrawnNode(identifier("node", number), f"DR-{name[0]}", f"Direction {name}", None)
        for number, name in enumerate(DIRECTIONS[:wanted], start=1)
    )
    services: list[DrawnNode] = []
    for number in range(len(directions) + 1, wanted + 1):
        rank = number - len(directions)
        direction = directions[(rank - 1) % len(directions)]
        label = Draw("node", number).choice(SERVICES)
        services.append(
            DrawnNode(
                identifier("node", number),
                f"{direction.code}-S{rank:02d}",
                f"{label} {direction.label.removeprefix('Direction ')} {rank:02d}",
                direction.node_id,
            )
        )
    return (*directions, *services)


def _role(number: int, base: Base, services: Sequence[UUID]) -> DrawnRole:
    draw = Draw("role", number)
    return DrawnRole(
        identifier("role", number),
        f"REF-R{number:03d}",
        f"{draw.choice(TRADES)} {number:03d}",
        services[(number - 1) % len(services)],
        draw.choice(base.rated),
        draw.choice(base.calendars),
        Decimal(draw.between(1, 12)),
    )


def _account(number: int, services: Sequence[UUID]) -> DrawnAccount:
    draw = Draw("account", number)
    first_name, last_name = draw.choice(FIRST_NAMES), draw.choice(LAST_NAMES)
    local = f"{_ascii(first_name)}.{_ascii(last_name)}.{number:03d}"
    return DrawnAccount(
        identifier("account", number),
        last_name,
        first_name,
        f"{local}@{WITNESS_DOMAIN}",
        services[(number - 1) % len(services)],
    )


def _ascii(name: str) -> str:
    """Give a name as the local part of an address writes it: lower case, without accents."""
    decomposed = unicodedata.normalize("NFKD", name.lower())
    return "".join(each for each in decomposed if each.isascii() and each.isalnum())
