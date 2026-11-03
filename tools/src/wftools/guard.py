# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Refuse a command of an agent that would stop what another agent started (US-1080).

The ``PreToolUse`` hook of ``.claude/settings.json`` runs it before every command of the ``Bash``
tool: ``python3 "$CLAUDE_PROJECT_DIR/tools/src/wftools/guard.py"``. It reads the JSON of the hook
on its input and refuses by the code 2, the reason on its error output; otherwise it says nothing
and returns 0. Claude Code lets a command pass on any other code: a JSON it cannot read, or a
failure of its own, lets the command pass, and only a decision refuses.

It depends on the standard library alone and imports no other module of ``wftools``: a fresh
worktree runs it before its environment is synchronised.

The line is cut into simple commands the way the shell runs them: at its operators, inside each
substitution — ``$( )``, backquotes, ``<( )`` —, inside the script of ``bash -c``, ``sh -c`` or
``zsh -c``, of ``eval`` and of ``trap``; past the assignments and the prefixes that run a command
(``sudo``, ``env``, ``timeout``, ``nohup``, ``xargs``…). Each command is then split into words by
``shlex``, and judged by the base name of its command word. Comments, redirections and the body of
a here-document run nothing, and are left out — the body of an unquoted one is still searched for
substitutions, which the shell runs. ``shlex`` cuts the words alone: its operators do not tell a
quoted ``;`` from one that ends a command, and ``kill 1 ';' $pid`` would hide its last target.
"""

import json
import re
import shlex
import sys
from collections.abc import Callable
from typing import NamedTuple, cast

RULE = (
    "An agent stops only what it started, by its PID or by a name of its own lot; never by "
    "pattern. A lock of git is not removed: the git command is run again."
)
INSTEAD = (
    "Instead: `kill <PID>` of a process you started; for what the Makefile started, the target "
    "that stops it: `make test-services-down`, `make service-down`, `make slot-release`."
)

# A substitution stands as this word in the command that holds it: its value is not known.
_SUBSTITUTED = "$(…)"
# Beyond this many nested substitutions or scripts, the line is judged as one not cut.
_MAX_DEPTH = 16
_BLANKS = frozenset(" \t\r")
_OPERATORS = frozenset(";&|()\n")
# The longest first: `<<-` before `<<`, `>>` before `>`.
_REDIRECTION = re.compile(r"&>>?|<<<|<<-?|<>|<&|<|>>|>&|>\||>")
_BACKSLASHED = re.compile(r"\\([\\`$])")
# What a line not cut is refused for naming: the command words of the forms refused.
_FORBIDDEN = re.compile(r"(?<![\w-])(?:pkill|killall|kill|docker|docker-compose)(?![\w-])|\.lock\b")
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
_PID = re.compile(r"-?[0-9]+")
_KEYWORDS = frozenset({"!", "{", "if", "then", "else", "elif", "do", "while", "until"})
_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
_CONTAINER_STOPS = frozenset({"rm", "remove", "stop", "kill", "restart"})
_COMPOSE_STOPS = frozenset({"down", "stop", "kill", "rm"})
# `kill -1` or `kill -0` alone reads as a signal without a target, or as a target: refused.
_LONE_TARGETS = frozenset({"-1", "-0"})


class _UnsplittableError(ValueError):
    """A line the guard cannot cut: an open quote or substitution, or one nested too deep."""


class _Heredoc(NamedTuple):
    """A here-document whose body follows the line that opens it."""

    delimiter: str
    tabs: bool
    expands: bool


class _Options(NamedTuple):
    """The options of a command that takes another command, or a subcommand, after them."""

    short: str = ""
    long: frozenset[str] = frozenset()
    operands: int = 0

    def skip(self, words: list[str], index: int) -> int:
        """Return the index of the word that follows the options and operands from ``index``."""
        while index < len(words):
            word = words[index]
            if word == "--":
                index += 1
                break
            # `-` alone is an operand, as standard input.
            if word == "-" or not word.startswith("-"):
                break
            if word.startswith("--"):
                index += 2 if word in self.long else 1
                continue
            # A cluster of short options: the first that takes an argument ends it, the rest of
            # the word being its argument, or the next word when it ends the cluster.
            cluster = word[1:]
            taking = next((at for at, char in enumerate(cluster) if char in self.short), None)
            index += 2 if taking == len(cluster) - 1 else 1
        return index + self.operands


# The commands that run the command that follows their options.
_PREFIXES = {
    "sudo": _Options(
        "CDghpRrTtUu",
        frozenset({"--chdir", "--chroot", "--close-from", "--command-timeout", "--group"})
        | frozenset({"--host", "--other-user", "--prompt", "--role", "--type", "--user"}),
    ),
    "doas": _Options("Cu"),
    "env": _Options("CSu", frozenset({"--chdir", "--split-string", "--unset"})),
    "nohup": _Options(),
    "nice": _Options("n", frozenset({"--adjustment"})),
    "timeout": _Options("ks", frozenset({"--kill-after", "--signal"}), operands=1),
    "time": _Options("fo", frozenset({"--format", "--output"})),
    "command": _Options(),
    "builtin": _Options(),
    "exec": _Options("a"),
    "setsid": _Options(),
    "stdbuf": _Options("eio", frozenset({"--error", "--input", "--output"})),
    "ionice": _Options("cn", frozenset({"--class", "--classdata"})),
    "xargs": _Options(
        "EILPadns",
        frozenset({"--arg-file", "--delimiter", "--max-args", "--max-chars", "--max-procs"})
        | frozenset({"--process-slot-var"}),
    ),
}
_DOCKER = _Options(
    "cHl",
    frozenset({"--config", "--context", "--host", "--log-level", "--tlscacert", "--tlscert"})
    | frozenset({"--tlskey"}),
)
_TRAP = _Options()
_COMPOSE = _Options(
    "fp",
    frozenset({"--ansi", "--env-file", "--file", "--parallel", "--profile", "--progress"})
    | frozenset({"--project-directory", "--project-name"}),
)


class _Scanner:
    """Cut a text of shell into its simple commands, appended to a list as their raw words.

    A substitution is cut in turn, its commands appended to the same list, and stands as
    ``$(…)`` in the word that holds it.
    """

    def __init__(self, text: str, commands: list[str], depth: int) -> None:
        if depth > _MAX_DEPTH:
            raise _UnsplittableError
        self.text = text
        self.commands = commands
        self.depth = depth
        self.position = 0
        self.heredocs: list[_Heredoc] = []

    def scan(self, start: int = 0, *, closing: bool = False) -> int:
        """Cut from ``start`` to the end, or to the ``)`` that closes a substitution."""
        text = self.text
        self.position = start
        words: list[str] = []
        nesting = 0
        while self.position < len(text):
            char = text[self.position]
            if char in _BLANKS:
                self.position += 1
            elif char == "#":
                end = text.find("\n", self.position)
                self.position = len(text) if end < 0 else end
            elif _redirects(text, self.position):
                self._redirection()
            elif char in _OPERATORS:
                self._close(words)
                self.position += 1
                if char == "(":
                    nesting += 1
                elif char == ")" and closing and nesting == 0:
                    return self.position
                elif char == ")":
                    nesting = max(nesting - 1, 0)
                elif char == "\n":
                    self._bodies()
            else:
                word = self._word()
                # `2>/dev/null`: the digits name the descriptor redirected, not an argument.
                if not (word.isdigit() and _redirects(text, self.position)):
                    words.append(word)
        if closing:
            raise _UnsplittableError
        self._close(words)
        return self.position

    def _close(self, words: list[str]) -> None:
        if words:
            self.commands.append(" ".join(words))
            words.clear()

    def _word(self) -> str:
        parts: list[str] = []
        text = self.text
        while self.position < len(text):
            char = text[self.position]
            if char in _BLANKS or char in _OPERATORS or _redirects(text, self.position):
                break
            parts.append(self._piece())
        return "".join(parts)

    def _piece(self) -> str:
        text, index = self.text, self.position
        char = text[index]
        if char == "\\":
            self.position = index + 2
            return "" if text.startswith("\\\n", index) else text[index : index + 2]
        if char == "'":
            end = text.find("'", index + 1)
            if end < 0:
                raise _UnsplittableError
            self.position = end + 1
            return text[index : end + 1]
        if char == '"':
            return self._double_quoted()
        if char == "`" or (char in "$<>" and text.startswith("(", index + 1)):
            self.position = (
                self._backquoted(index + 1) if char == "`" else self._substitution(index + 2)
            )
            return _SUBSTITUTED
        self.position = index + 1
        return char

    def _double_quoted(self) -> str:
        text = self.text
        index = self.position + 1
        parts = ['"']
        while index < len(text):
            char = text[index]
            if char == '"':
                self.position = index + 1
                return "".join([*parts, '"'])
            if char == "\\":
                parts.append(text[index : index + 2])
                index += 2
            elif char == "`":
                index = self._backquoted(index + 1)
                parts.append(_SUBSTITUTED)
            elif text.startswith("$(", index):
                index = self._substitution(index + 2)
                parts.append(_SUBSTITUTED)
            else:
                parts.append(char)
                index += 1
        raise _UnsplittableError

    def _substitution(self, start: int) -> int:
        return _Scanner(self.text, self.commands, self.depth + 1).scan(start, closing=True)

    def _backquoted(self, start: int) -> int:
        text = self.text
        index = start
        while index < len(text):
            if text[index] == "\\":
                index += 2
            elif text[index] == "`":
                inner = _BACKSLASHED.sub(r"\1", text[start:index])
                _Scanner(inner, self.commands, self.depth + 1).scan()
                return index + 1
            else:
                index += 1
        raise _UnsplittableError

    def _redirection(self) -> None:
        text = self.text
        heredoc = text.startswith("<<", self.position) and not text.startswith("<<<", self.position)
        tabs = text.startswith("<<-", self.position)
        match = _REDIRECTION.match(text, self.position)
        self.position = match.end() if match else self.position + 1
        while self.position < len(text) and text[self.position] in _BLANKS:
            self.position += 1
        # The target is no argument of the command; a substitution in it still runs.
        target = self._word()
        if heredoc:
            delimiter = re.sub(r"[\\'\"]", "", target)
            self.heredocs.append(_Heredoc(delimiter, tabs, expands=delimiter == target))

    def _bodies(self) -> None:
        """Pass the bodies of the here-documents opened on the line that just ended."""
        text = self.text
        for heredoc in self.heredocs:
            while self.position < len(text):
                end = text.find("\n", self.position)
                end = len(text) if end < 0 else end
                line = text[self.position : end]
                if (line.lstrip("\t") if heredoc.tabs else line) == heredoc.delimiter:
                    self.position = end + 1
                    break
                stop = self._expansions(end) if heredoc.expands else end
                following = text.find("\n", stop)
                self.position = len(text) if following < 0 else following + 1
        self.heredocs.clear()

    def _expansions(self, end: int) -> int:
        """Cut the substitutions of a line of an unquoted body; return where they stop."""
        text = self.text
        index = self.position
        while index < end:
            if text[index] == "\\":
                index += 2
            elif text[index] == "`":
                index = self._backquoted(index + 1)
            elif text.startswith("$(", index):
                index = self._substitution(index + 2)
            else:
                index += 1
        return max(index, end)


def _redirects(text: str, index: int) -> bool:
    """Say whether a redirection starts at ``index``: ``<( )`` and ``>( )`` are substitutions."""
    return text.startswith("&>", index) or (
        text[index : index + 1] in {"<", ">"} and not text.startswith("(", index + 1)
    )


def refusal(command: str) -> str | None:
    """Return the refused form a command line takes, or None when it may run."""
    return _line(command, 0)


def _line(text: str, depth: int) -> str | None:
    commands: list[str] = []
    try:
        _Scanner(text, commands, depth).scan()
        split = [shlex.split(command) for command in commands]
    except ValueError:
        found = _FORBIDDEN.search(text)
        return None if found is None else f"a line it cannot cut, which names `{found.group()}`"
    return next((form for words in split if (form := _simple(words, depth)) is not None), None)


def _simple(words: list[str], depth: int) -> str | None:
    """Judge a simple command, past its assignments and the prefixes that run it."""
    piped = False
    index = 0
    while index < len(words):
        word = words[index]
        name = word.rsplit("/", 1)[-1]
        if _ASSIGNMENT.match(word) or word in _KEYWORDS:
            index += 1
        elif name in _PREFIXES:
            # What `xargs` runs takes its arguments from the pipe: they are never literal.
            piped = piped or name == "xargs"
            index = _PREFIXES[name].skip(words, index + 1)
        else:
            check = _CHECKS.get(name)
            command = _Command(name, words[index + 1 :], piped=piped, depth=depth)
            return None if check is None else check(command)
    return None


class _Command(NamedTuple):
    """A simple command to judge: the base name of its command word, and its arguments."""

    name: str
    arguments: list[str]
    piped: bool
    """Run by ``xargs``: its arguments come from a pipe."""
    depth: int


def _pattern(command: _Command) -> str | None:
    return f"`{command.name}`: it stops processes by a pattern"


def _fuser(command: _Command) -> str | None:
    killing = any(
        word == "--kill" or (word[:1] == "-" and word[1:2] != "-" and "k" in word[1:])
        for word in command.arguments
    )
    return "`fuser -k`: it stops the processes that hold a file or a port" if killing else None


def _kill(command: _Command) -> str | None:
    if command.piped:
        return "`kill` run by `xargs`: its targets come from a pipe"
    for target in _kill_targets(command.arguments):
        if not _PID.fullmatch(target):
            return f"`kill {target}`: a target of `kill` is a PID written in digits"
        if int(target) in {0, -1}:
            return f"`kill {target}`: it signals every process of the user, or of its group"
    return None


def _kill_targets(arguments: list[str]) -> list[str]:
    """Return the targets of a ``kill``: the first option is its signal, ``--`` ends them."""
    first = arguments[0] if arguments else ""
    if first in {"-l", "-L", "--list", "--table"} or first.startswith("--list="):
        return []
    if first in {"-s", "-n", "--signal"}:
        targets = arguments[2:]
    elif first.startswith("-") and first != "--":
        targets = arguments[1:]
    else:
        targets = arguments
    if targets[:1] == ["--"]:
        targets = targets[1:]
    return targets if targets or first not in _LONE_TARGETS else [first]


def _docker(command: _Command) -> str | None:
    words = command.arguments[_DOCKER.skip(command.arguments, 0) :]
    if not words:
        return None
    if words[0] == "compose":
        return _compose(command._replace(name="docker compose", arguments=words[1:]))
    # `docker container stop` is `docker stop`.
    container = words[0] == "container" and len(words) > 1
    verb, rest = (words[1], words[2:]) if container else (words[0], words[1:])
    if "prune" in {verb, *rest[:1]}:
        return "`docker … prune`: it removes what the other lots hold"
    if verb in _CONTAINER_STOPS:
        return _container_stop(verb, rest, piped=command.piped)
    return None


def _container_stop(verb: str, arguments: list[str], *, piped: bool) -> str | None:
    if piped:
        return f"`docker {verb}` run by `xargs`: its targets come from a pipe"
    for argument in arguments:
        if argument == "--filter" or argument.startswith("--filter="):
            return f"`docker {verb} --filter`: its targets come from a filter"
        if any(char in argument for char in "$`*?["):
            return f"`docker {verb} {argument}`: a target is a literal name or identifier"
    return None


def _compose(command: _Command) -> str | None:
    arguments = command.arguments
    index = _COMPOSE.skip(arguments, 0)
    if index < len(arguments) and arguments[index] in _COMPOSE_STOPS:
        return (
            f"`{command.name} {arguments[index]}` outside the Makefile: the Makefile alone stops "
            "a platform, under the project name of its lot"
        )
    return None


def _unlink(command: _Command) -> str | None:
    for argument in command.arguments:
        directories, _, last = argument.rpartition("/")
        lock = last.endswith(".lock")
        in_git = ".git" in directories.split("/")
        # A directory computed by a substitution or a variable is `git rev-parse --git-dir`.
        if (in_git and (lock or last[-1:] in {"*", "?", "]"})) or (lock and "$" in directories):
            return (
                f"`{command.name} {argument}`: a lock of git is held by a git command that runs, "
                "maybe in another worktree"
            )
    return None


def _shell(command: _Command) -> str | None:
    """Judge the script of ``bash -c``, ``sh -c`` and their like; a script file is not read."""
    arguments = command.arguments
    index = 0
    scripted = False
    while index < len(arguments):
        word = arguments[index]
        if word in {"-o", "+o", "-O", "+O"}:
            index += 2
        elif word in {"-", "--"}:
            index += 1
            break
        elif len(word) > 1 and word[0] in "-+":
            scripted = scripted or (word[0] == "-" and word[1] != "-" and "c" in word)
            index += 1
        else:
            break
    if scripted and index < len(arguments):
        return _line(arguments[index], command.depth + 1)
    return None


def _eval(command: _Command) -> str | None:
    return _line(" ".join(command.arguments), command.depth + 1)


def _trap(command: _Command) -> str | None:
    """Judge the action of ``trap``, which the shell runs on its signal: ``trap 'kill 0' EXIT``."""
    arguments = command.arguments[_TRAP.skip(command.arguments, 0) :]
    return _line(arguments[0], command.depth + 1) if arguments else None


_CHECKS: dict[str, Callable[[_Command], str | None]] = {
    "pkill": _pattern,
    "killall": _pattern,
    "fuser": _fuser,
    "kill": _kill,
    "docker": _docker,
    "docker-compose": _compose,
    "rm": _unlink,
    "unlink": _unlink,
    "eval": _eval,
    "trap": _trap,
} | dict.fromkeys(_SHELLS, _shell)


def _command_of(event: object) -> str | None:
    """Return the command of the ``Bash`` tool the hook's JSON carries, if it carries one."""
    if isinstance(event, dict):
        tool_input = cast("dict[str, object]", event).get("tool_input")
        if isinstance(tool_input, dict):
            command = cast("dict[str, object]", tool_input).get("command")
            if isinstance(command, str):
                return command
    return None


def main() -> int:
    """Read the hook's JSON; return 2, the reason on the error output, when it is refused."""
    try:
        event: object = json.load(sys.stdin)
    except ValueError:
        return 0
    command = _command_of(event)
    form = None if command is None else refusal(command)
    if form is None:
        return 0
    sys.stderr.write(f"Refused by the command guard (US-1080): {form}.\n{RULE}\n{INSTEAD}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
