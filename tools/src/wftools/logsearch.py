# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Search logs and texts: the secrets and tokens known, and the story of one identifier (US-2900).

Usage::

    python -m wftools.logsearch secrets [--name VARIABLE ...] [FILE ...]
    python -m wftools.logsearch follow IDENTIFIER [FILE ...]
    python -m wftools.logsearch fields [FILE ...]

Without a file, the text is read from the standard input — ``make service-logs`` gives it —; a
file is read as it stands, a directory in every file it holds.

``secrets`` looks for the value of each known secret — the variables the platform is started
with (``SECRET_VARIABLES``) — in the text, as it is written, as JSON escapes it and as a URL
quotes it, and for the shape of a token whatever its value (a JWT, a bearer credential). It
prints what it found by the name of the variable, never the value, and ends with 1 if it found
anything, with 2 if the text is empty or no secret is known; it names, on the standard error, the
variables it left out, absent or too short. ``fields`` ends with 2 on an empty text too.
``find_secrets`` is the same search for a caller that holds the text and the secrets:
the search of the logs of the platform (WF-OBS-0020, US-2900) and that of the repository
(WF-SEC-0010, US-2840) are this one.

``follow`` prints the lines of the logs of an identifier of correlation, and those that name what
they name — the deposit a file was made under, the import, the task (``LINKS``) —: the story of an
import by the identifier its user was given. Records are JSON lines, which Compose may prefix with
the name of the service.

``fields`` checks the records of the services of Waterfall — the API, the worker and the service
of the restoration —: each line is a record that carries what WF-OBS-0020 asks of every one, the
correlation identifier, the author of the action and the severity (``REQUIRED``; the project is
named when there is one). It prints the lines that fail, and ends with 1 if there is one.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.parse import quote, quote_plus

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

SECRET_VARIABLES = (
    "WATERFALL_POSTGRES_PASSWORD",
    "WATERFALL_SERVICE_DATABASE_PASSWORD",
    "WATERFALL_BACKUP_DATABASE_PASSWORD",
    "WATERFALL_REDIS_PASSWORD",
    "WATERFALL_KEYCLOAK_DATABASE_PASSWORD",
    "WATERFALL_STORAGE_ACCESS_KEY",
    "WATERFALL_STORAGE_SECRET",
    "WATERFALL_STORAGE_RPC_SECRET",
    "WATERFALL_KEYCLOAK_ADMIN_PASSWORD",
    "WATERFALL_FRONT_CLIENT_SECRET",
    "WATERFALL_SERVICE_CLIENT_SECRET",
    "WATERFALL_INSTALLATION_CLIENT_SECRET",
)
"""The secrets of the platform of service, which the guide lists (« Commandes »)."""

FIXED_SECRETS = {"E2E_LOCAL_PASSWORD": "k7#Qw2ZpX9vR"}
"""The passwords of the accounts of the paths, which no variable holds: the constant of the paths
(``frontend/e2e/service/realm.ts``, ``LOCAL_PASSWORD``), which the administrator of the
installation and the local accounts of the realm are given; a test keeps the two equal."""

SHORTEST = 6
"""A value shorter than this is not searched for: it would be found in any text."""

TOKENS = {
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "bearer": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
}
"""The shapes of the tokens the platform exchanges: a signed token, an Authorization header."""

REQUIRED = ("correlation_id", "actor", "level")
"""What every record of the services of Waterfall carries (WF-OBS-0020)."""

LINKS = ("upload_id", "import_id", "task_id")
"""What a record names that other records, under other correlations, name too."""


def secrets_from(
    environment: Mapping[str, str], names: Iterable[str] = SECRET_VARIABLES
) -> dict[str, str]:
    """Give, by variable name, the values of the secrets the environment holds."""
    return {name: value for name in names if len(value := environment.get(name, "")) >= SHORTEST}


def left_out(environment: Mapping[str, str], names: Iterable[str] = SECRET_VARIABLES) -> list[str]:
    """Name the variables ``secrets_from`` leaves out: absent, or too short to be searched for."""
    return [name for name in names if len(environment.get(name, "")) < SHORTEST]


def spellings(value: str) -> set[str]:
    """Give the ways a value is written in a log: as it is, escaped as JSON, quoted as a URL."""
    return {value, json.dumps(value)[1:-1], quote(value, safe=""), quote_plus(value)}


def find_secrets(text: str, secrets: Mapping[str, str]) -> list[str]:
    """Name the secrets and the tokens a text carries; the values are never given back.

    ``secrets`` maps a name to the value to look for. A token is named by its shape.
    """
    found = [
        name
        for name, value in secrets.items()
        if value and any(spelling in text for spelling in spellings(value))
    ]
    return found + [name for name, shape in TOKENS.items() if shape.search(text)]


def record_of(line: str) -> dict[str, object] | None:
    """Read the JSON record a line holds, after the prefix Compose gives it, if it holds one."""
    start = line.find("{")
    if start < 0:
        return None
    try:
        record: object = json.loads(line[start:])
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict):
        return None
    return {str(key): value for key, value in cast("dict[object, object]", record).items()}


def follow(lines: Sequence[str], identifier: str) -> list[str]:
    """Give, in order, the lines of a correlation and those that name what its lines name.

    A line that is no record is kept when it holds the identifier itself.
    """
    records = [record_of(line) for line in lines]
    mine = {
        number
        for number, (line, record) in enumerate(zip(lines, records, strict=True))
        if (record is not None and record.get("correlation_id") == identifier)
        or (record is None and identifier in line)
    }
    named = {
        str(value)
        for number in mine
        if (record := records[number]) is not None
        for key, value in record.items()
        if key in LINKS
    }
    return [
        line
        for number, (line, record) in enumerate(zip(lines, records, strict=True))
        if number in mine
        or (
            record is not None
            and named & {str(value) for key, value in record.items() if key in LINKS}
        )
    ]


def lacking(lines: Iterable[str]) -> list[str]:
    """Give the non-empty lines that are no record, or a record without a required field."""
    wrong: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        record = record_of(line)
        if record is None or any(key not in record for key in REQUIRED):
            wrong.append(line)
    return wrong


def read_texts(paths: Sequence[str]) -> str:
    """Read the files, the directories in every file they hold, or the standard input."""
    if not paths:
        return sys.stdin.read()
    files = [
        each
        for path in map(Path, paths)
        for each in (sorted(path.rglob("*")) if path.is_dir() else [path])
        if each.is_file()
    ]
    return "\n".join(each.read_text(encoding="utf-8", errors="replace") for each in files)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the search the command line asks for; 1 if a secret was found."""
    parser = argparse.ArgumentParser(prog="wftools.logsearch", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    secret = commands.add_parser("secrets", help="look for the secrets and tokens known")
    secret.add_argument("--name", action="append", help="a variable that holds a secret")
    secret.add_argument("files", nargs="*")
    story = commands.add_parser("follow", help="print the story of a correlation identifier")
    story.add_argument("identifier")
    story.add_argument("files", nargs="*")
    fields = commands.add_parser("fields", help="check that every record carries its fields")
    fields.add_argument("files", nargs="*")
    arguments = parser.parse_args(argv)
    text = read_texts(arguments.files)
    if arguments.command != "follow" and not text.strip():
        # An empty text — a reading of the logs that failed — would pass whatever was searched for.
        print("the text is empty: nothing was read, so nothing can be checked", file=sys.stderr)
        return 2
    if arguments.command == "fields":
        wrong = lacking(text.splitlines())
        print("\n".join(wrong), file=sys.stderr)
        print(f"{len(wrong)} lines without {', '.join(REQUIRED)} in {len(text.splitlines())}")
        return 1 if wrong else 0
    if arguments.command == "follow":
        print("\n".join(follow(text.splitlines(), arguments.identifier)))
        return 0
    names = arguments.name or SECRET_VARIABLES
    known = secrets_from(os.environ, names)
    skipped = left_out(os.environ, names)
    if skipped:
        print(f"not searched, absent or too short: {', '.join(skipped)}", file=sys.stderr)
    if not known:
        # A search with nothing to look for finds nothing: it would pass whatever the text holds.
        print("no secret to look for: the variables of the platform are not set", file=sys.stderr)
        return 2
    if not arguments.name:
        known |= FIXED_SECRETS
    found = find_secrets(text, known)
    for name in found:
        print(f"found in the text: {name}", file=sys.stderr)
    print(f"searched {len(known)} secrets and the shapes of tokens in {len(text)} characters")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
