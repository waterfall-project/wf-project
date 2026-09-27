# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""List the numeric examples of the Vérif fields, and check the fixtures that cite them.

Usage: ``python -m wftools.examples [--write]``.

A numeric example is a sentence of a Vérif field that carries a number — other than the
number of an identifier, a section or a function code. Each is a test case of the core
(WF-QUA-0020). The listing, ``fixtures/examples.json``, is generated: each example under a
key made of its requirement and the fingerprint of its text, so that a sentence edited in
the document gets a new key, and the fixture of the old one fails instead of passing
unnoticed. The rank of a sentence stays out of the key: inserting a sentence would shift
the others and fail fixtures of sentences nobody changed.

A fixture is a JSON file under ``fixtures/`` that names, in ``examples``, the keys of the
sentences it carries; its data is written by hand, from the sentence. With ``--write``, the
listing is regenerated. Without it, the listing is checked against the document, every key
a fixture cites must exist, and the examples no fixture cites yet are reported.
"""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from wftools import REPOSITORY, projection

FIXTURES = REPOSITORY / "fixtures"
LISTING = FIXTURES / "examples.json"

# What carries digits without being a number of the example: identifiers, section
# references, function and flow codes, flexibility levels.
_CODES = re.compile(
    r"WF-[A-Z]+-\d{4}(?:-[A-Z])?|(?:FBS|PBS|FLX)-\d+(?:\.\d+)*|§\s?\d+(?:\.\d+)*|\bF[012]\b",
)
_DIGIT = re.compile(r"\d")


@dataclass(frozen=True, slots=True)
class Example:
    """A numeric example: one sentence of the Vérif field of one requirement."""

    requirement: str
    sentence: str

    @property
    def key(self) -> str:
        """Return the key a fixture cites: the requirement and the fingerprint of the text."""
        digest = hashlib.sha256(self.sentence.encode("utf-8")).hexdigest()[:12]
        return f"{self.requirement}#{digest}"


def is_numeric(sentence: str) -> bool:
    """Whether a sentence carries a number other than an identifier or a code."""
    return bool(_DIGIT.search(_CODES.sub("", sentence)))


def examples(requirements: tuple[projection.Requirement, ...]) -> list[Example]:
    """Return the numeric examples of the document, in the order of the document."""
    return [
        Example(requirement.identifier, sentence)
        for requirement in requirements
        if not requirement.is_example
        for sentence in requirement.verification_sentences
        if is_numeric(sentence)
    ]


def listing(found: list[Example]) -> str:
    """Return the text of the generated listing."""
    entries = [
        {"key": example.key, "requirement": example.requirement, "sentence": example.sentence}
        for example in found
    ]
    document = {"generated_by": "make fixtures", "examples": entries}
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def cited(fixtures: Path = FIXTURES) -> dict[str, list[str]]:
    """Return, for each fixture that cites examples, the keys it cites."""
    found: dict[str, list[str]] = {}
    for path in sorted(fixtures.rglob("*.json")):
        if path == LISTING:
            continue
        data = cast("object", json.loads(path.read_text(encoding="utf-8")))
        if isinstance(data, dict) and "examples" in data:
            fields = cast("dict[str, object]", data)
            found[path.relative_to(REPOSITORY).as_posix()] = _keys(path, fields["examples"])
    return found


def _keys(path: Path, keys: object) -> list[str]:
    items = cast("list[object]", keys) if isinstance(keys, list) else None
    if items is None or not all(isinstance(key, str) for key in items):
        message = f"{path}: `examples` must be a list of keys"
        raise ValueError(message)
    return [str(key) for key in items]


def check(found: list[Example], fixtures: dict[str, list[str]]) -> list[str]:
    """Return the problems: an outdated listing, or a fixture citing a key that is gone."""
    problems: list[str] = []
    if not LISTING.exists() or LISTING.read_text(encoding="utf-8") != listing(found):
        problems.append(f"{LISTING.relative_to(REPOSITORY)} is outdated: run make fixtures")
    keys = {example.key for example in found}
    problems.extend(
        f"{fixture}: cites {key}, which is no sentence of the document any more"
        for fixture, cited_keys in fixtures.items()
        for key in cited_keys
        if key not in keys
    )
    return problems


def main(arguments: list[str]) -> int:
    """Write the listing, or check it and the fixtures, and report what is not covered."""
    parser = argparse.ArgumentParser(
        prog="wftools.examples", description="List and check the numeric examples."
    )
    parser.add_argument("--write", action="store_true", help="regenerate the listing")
    options = parser.parse_args(arguments)
    found = examples(projection.read())
    if options.write:
        FIXTURES.mkdir(exist_ok=True)
        LISTING.write_text(listing(found), encoding="utf-8")
        print(f"{LISTING.relative_to(REPOSITORY)}: {len(found)} numeric examples")
        return 0
    fixtures = cited()
    problems = check(found, fixtures)
    for problem in problems:
        print(problem, file=sys.stderr)
    covered = {key for keys in fixtures.values() for key in keys}
    uncovered = [example for example in found if example.key not in covered]
    print(f"{len(found)} numeric examples, {len(found) - len(uncovered)} cited by a fixture")
    for example in uncovered:
        print(f"  not covered  {example.key}  {example.sentence[:70]}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
