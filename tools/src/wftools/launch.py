# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Run a tool of the repository by the ``python3`` of the workstation, whatever its age (US-2450).

The ``PreToolUse`` hook of ``.claude/settings.json`` runs ``launch.py guard`` before every command
of the ``Bash`` tool, and the Makefile runs ``launch.py slots …`` (``SLOTS``): both by ``python3``,
outside ``uv run``, the interpreter of the workstation or of the runner. The tools are written in
the syntax of Python 3.14, which an older interpreter cannot import: ``guard.py`` failed on a
``NameError``, by the code 1, that Claude Code takes for a failure of the hook and lets the command
pass (#3711); ``slots.py`` failed on a ``SyntaxError`` that the Makefile threw away (#3719).

This file is written in the syntax of Python 3.8, with annotations an old interpreter evaluates
(a test reads it with the grammar of 3.8), and imports the standard library alone. It checks the
version of the interpreter, then runs the tool named, as ``python3 <tool>.py`` would.

The guard fails closed: under a Python older than 3.14, or when it raises while it judges a
command — or ends by any code but 0 or 2 —, the command is refused by the code 2, the reason on
the error output. What happens before this file runs, or past it, it cannot see: no ``python3``
on the ``PATH``, one too old to read this very file, an error of ``main`` itself, a process
killed. The hook covers them by its shell, ``launch.py guard || exit 2``: 0 stays 0, any other
code becomes the refusal. The slots say the version they expect and end by the code 2.
"""

import runpy
import sys
from pathlib import Path

REQUIRED = (3, 14)
TOOLS = ("guard", "slots")
REFUSED = 2
"""The code by which Claude Code refuses a command; the slots end by it on a setting too."""


def _version() -> str:
    """Return the version of this interpreter, and where it stands."""
    major, minor, micro = sys.version_info[:3]
    return f"{major}.{minor}.{micro} ({sys.executable or 'python3'})"


def _too_old(tool: str) -> int:
    """Say that the tool cannot run under this interpreter, and which version it expects."""
    expected = f"{REQUIRED[0]}.{REQUIRED[1]}"
    if tool == "guard":
        sys.stderr.write(
            f"Refused: the command guard cannot be used, it needs Python {expected} and python3 "
            f"is {_version()}. Every command is refused until python3 is Python {expected} "
            "(make check-tools).\n"
        )
    else:
        sys.stderr.write(
            f"slots: the tool of the slots did not run, it needs Python {expected} and python3 "
            f"is {_version()}.\n"
        )
    return REFUSED


def _guard(path: str) -> int:
    """Run the guard; refuse the command when it gives no decision of its own (fail closed)."""
    try:
        runpy.run_path(path, run_name="__main__")
    except SystemExit as ending:
        if ending.code in (0, REFUSED):
            raise
        sys.stderr.write(
            f"Refused: the command guard ended by the code {ending.code!r}, which is no "
            "decision; a command it cannot judge is refused.\n"
        )
        raise SystemExit(REFUSED) from ending
    except BaseException as error:
        sys.stderr.write(
            f"Refused: the command guard failed while judging the command "
            f"({type(error).__name__}: {error}); a command it cannot judge is refused.\n"
        )
        raise SystemExit(REFUSED) from error
    sys.stderr.write("Refused: the command guard ended without a decision.\n")
    return REFUSED


def main() -> int:
    """Run the tool named by the first argument; return the code of a refusal or a failure."""
    tool = sys.argv[1] if len(sys.argv) > 1 else ""
    if tool not in TOOLS:
        sys.stderr.write(f"launch: name a tool among {', '.join(TOOLS)}, not {tool!r}.\n")
        return REFUSED
    if sys.version_info < REQUIRED:
        return _too_old(tool)
    path = str(Path(__file__).resolve().with_name(tool + ".py"))
    sys.argv = [path, *sys.argv[2:]]
    if tool == "guard":
        return _guard(path)
    # slots.py ends by sys.exit, whose SystemExit passes through main with its code: the return
    # below is never reached, it only gives main the int its signature promises.
    runpy.run_path(path, run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
