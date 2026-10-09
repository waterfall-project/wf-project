# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Read the requirements of the specification from its Markdown projection.

The projection, ``docs/spec/waterfall-spec.md``, is generated from the Word document. It
carries each requirement as a fenced block tagged ``yaml exigence``, one ``field: "value"``
per line, with the field names of the document, in French. Every tool that needs the
requirements reads them here: one reading of the document, not one per tool, so that two
tools cannot disagree on what a requirement says.

It reads the functional breakdown (FBS) here too, for the same reason: the functions of the
document, which the requirements cite and the screens address.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from wftools import REPOSITORY

PROJECTION = REPOSITORY / "docs" / "spec" / "waterfall-spec.md"

EXAMPLE_IDENTIFIER = "WF-EXA-0010-A"
"""The requirement of section 1.3.1, which shows the form of a requirement.

It is not a requirement of the product: a tool that counts, covers or checks requirements
leaves it out, or it would ask for a test of something that does not exist.
"""

MANDATORY = "F0"
"""The flexibility of a requirement that must be met, as opposed to F1 and F2 (§1.3.1)."""

_FIELDS = {
    "section": "section",
    "id": "identifier",
    "titre": "title",
    "flexibilite": "flexibility",
    "fbs": "fbs",
    "pbs": "pbs",
    "corps": "body",
    "motif": "motive",
    "verification": "verification",
}
_BLOCK = re.compile(r"^```yaml exigence\n(.*?)^```", re.MULTILINE | re.DOTALL)
_FIELD = re.compile(r'^(\w+): "(.*)"$', re.MULTILINE)
_IDENTIFIER = re.compile(r"^(WF-[A-Z]+-\d{4})-([A-Z])$")
# A function of the FBS is named by its box in a figure — the figure of the tree, which stops
# at the second level of the projects, or the figure of its block —, ``FBS_1_1_Gestion_des_
# utilisateurs["FBS-1.1<br>Gestion des utilisateurs"]``, under it by an arrow from its parent's
# box; and by the heading of its paragraph, when it has one (not FBS-4.9): ``##### 3.4.4.1.1.
# FBS-3.1.1 : Nature et catégories de coûts``, Word putting a non-breaking space before the colon.
_FBS_HEADING = re.compile(r"^#+ [\d.]+ (FBS-\d+(?:\.\d+)*)\s*:\s*(.+)$", re.MULTILINE)
_FBS_BOX = re.compile(r'^\s*(\w+)\["(FBS-\d+(?:\.\d+)*)<br>([^"]+)"\]', re.MULTILINE)
_FBS_ARROW = re.compile(r"^\s*(\w+) --> (\w+)\s*$", re.MULTILINE)
# A sentence ends on a full stop, a question or an exclamation mark, followed by a space and
# by what can open a French sentence. A full stop inside a section number (§4.4.1) or a
# decimal comma (0,917) is never followed by a space, and so never ends a sentence.
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ«0-9])")
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
_SPACES = re.compile(r"[\s   ]+")


class ProjectionError(ValueError):
    """The projection does not have the shape this reader expects."""


def normalize(text: str) -> str:
    """Return the text with typographic apostrophes and spaces made plain.

    Word writes « L’API » with a typographic apostrophe and non-breaking spaces around
    quotation marks; a hand-written file writes « L'API ». Two texts are compared once both
    are normalized, so that a quotation is not refused for a character nobody can see.
    """
    return _SPACES.sub(" ", text.translate(_APOSTROPHES)).strip()


def sentences(text: str) -> tuple[str, ...]:
    """Split a text into its sentences, each normalized."""
    return tuple(part for part in _SENTENCE_BREAK.split(normalize(text)) if part)


@dataclass(frozen=True, slots=True)
class Requirement:
    """A requirement as the document states it."""

    section: str
    identifier: str
    title: str
    flexibility: str
    fbs: str
    pbs: str
    body: str
    motive: str
    verification: str

    @property
    def key(self) -> str:
        """The identifier without its revision letter: ``WF-ARC-0010``."""
        return self.identifier[:-2]

    @property
    def revision(self) -> str:
        """The revision letter of the identifier: ``A``."""
        return self.identifier[-1]

    @property
    def is_example(self) -> bool:
        """Whether this is the example of section 1.3.1 rather than a product requirement."""
        return self.identifier == EXAMPLE_IDENTIFIER

    @property
    def is_mandatory(self) -> bool:
        """Whether this is an F0 requirement of the product."""
        return self.flexibility == MANDATORY and not self.is_example

    @property
    def verification_sentences(self) -> tuple[str, ...]:
        """The sentences of the Vérif field, normalized, in the order of the document."""
        return sentences(self.verification)


@dataclass(frozen=True, slots=True)
class Function:
    """A function of the functional breakdown (§3.4.1), by its code and its name."""

    code: str
    label: str

    def is_under(self, other: "Function") -> bool:
        """Whether this function is below another in the tree: FBS-4.3.1 under FBS-4.3."""
        return self.code.startswith(f"{other.code}.")


def functions(text: str) -> tuple[Function, ...]:
    """Read every function of the FBS of a projection, in the order of their codes.

    The figures name every function; a heading that names one they missed adds it all the same,
    a protection that costs nothing. A function keeps the name of its heading, the figures drawing
    it in fewer words. Raises ProjectionError when the projection names none, and on an arrow of a
    figure whose child does not extend the code of its parent by one level.
    """
    named: dict[str, str] = {}
    for code, label in _FBS_HEADING.findall(text):
        named.setdefault(code, normalize(label))
    for _box, code, label in _FBS_BOX.findall(text):
        named.setdefault(code, normalize(label))
    for parent, child in arrows(text):
        _extends(parent, child)
    if not named:
        message = "the projection names no function of the FBS"
        raise ProjectionError(message)
    order = sorted(named, key=lambda code: tuple(int(part) for part in code[4:].split(".")))
    return tuple(Function(code, named[code]) for code in order)


def arrows(text: str) -> tuple[tuple[str, str], ...]:
    """Return the arrows of the figures from a function to another, by codes: (parent, child)."""
    boxes = {box: code for box, code, _label in _FBS_BOX.findall(text)}
    return tuple(
        (boxes[parent], boxes[child])
        for parent, child in _FBS_ARROW.findall(text)
        if parent in boxes and child in boxes
    )


def _extends(parent: str, child: str) -> None:
    """Raise ProjectionError unless a code extends its parent's by one level: FBS-4.3, FBS-4.3.1."""
    if child.rpartition(".")[0] != parent:
        message = f"the figure puts {child} under {parent}, whose code it does not extend"
        raise ProjectionError(message)


def leaves(tree: tuple[Function, ...]) -> tuple[Function, ...]:
    """Return the functions of a tree that no other function is under, in its order."""
    return tuple(fn for fn in tree if not any(other.is_under(fn) for other in tree))


def read_functions(path: Path = PROJECTION) -> tuple[Function, ...]:
    """Read every function of the FBS of the projection file, in the order of their codes."""
    return functions(path.read_text(encoding="utf-8"))


def parse(text: str) -> tuple[Requirement, ...]:
    """Read every requirement of a projection, in the order of the document.

    Raises ProjectionError on a block that lacks a field, carries an unknown one, has a
    malformed identifier, or repeats the identifier of an earlier block.
    """
    requirements: list[Requirement] = []
    seen: set[str] = set()
    for number, block in enumerate(_BLOCK.findall(text), start=1):
        requirement = _requirement(number, block)
        if requirement.identifier in seen:
            message = f"requirement {requirement.identifier} appears twice"
            raise ProjectionError(message)
        seen.add(requirement.identifier)
        requirements.append(requirement)
    return tuple(requirements)


def read(path: Path = PROJECTION) -> tuple[Requirement, ...]:
    """Read every requirement of the projection file, in the order of the document."""
    return parse(path.read_text(encoding="utf-8"))


def _requirement(number: int, block: str) -> Requirement:
    fields = dict(_FIELD.findall(block))
    unknown = fields.keys() - _FIELDS.keys()
    missing = _FIELDS.keys() - fields.keys()
    if unknown or missing:
        message = (
            f"requirement block {number}: missing {sorted(missing)}, unknown {sorted(unknown)}"
        )
        raise ProjectionError(message)
    if not _IDENTIFIER.match(fields["id"]):
        message = f"requirement block {number}: malformed identifier {fields['id']!r}"
        raise ProjectionError(message)
    return Requirement(**{_FIELDS[name]: value for name, value in fields.items()})
