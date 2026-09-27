# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Read the requirements of the specification from its Markdown projection.

The projection, ``docs/spec/waterfall-spec.md``, is generated from the Word document. It
carries each requirement as a fenced block tagged ``yaml exigence``, one ``field: "value"``
per line, with the field names of the document, in French. Every tool that needs the
requirements reads them here: one reading of the document, not one per tool, so that two
tools cannot disagree on what a requirement says.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from wftools import REPOSITORY

PROJECTION = REPOSITORY / "docs" / "spec" / "waterfall-spec.md"

EXAMPLE_IDENTIFIER = "WF-EXAMP-0010-A"
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
            f"requirement block {number}: "
            f"missing {sorted(missing)}, unknown {sorted(unknown)}"
        )
        raise ProjectionError(message)
    if not _IDENTIFIER.match(fields["id"]):
        message = f"requirement block {number}: malformed identifier {fields['id']!r}"
        raise ProjectionError(message)
    return Requirement(**{_FIELDS[name]: value for name, value in fields.items()})
