# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Refuse a command of an agent that would stop what another agent started (US-1080, US-1310).

The ``PreToolUse`` hook of ``.claude/settings.json`` runs it before every command of the ``Bash``
tool: ``python3 "$CLAUDE_PROJECT_DIR/tools/src/wftools/guard.py"``. It reads the JSON of the hook
on its input and refuses by the code 2, the reason on its error output; otherwise it says nothing
and returns 0. Claude Code lets a command pass on any other code: a JSON it cannot read, or a
failure of its own, lets the command pass, and only a decision refuses.

It depends on the standard library alone and imports no other module of ``wftools``: a fresh
worktree runs it before its environment is synchronised.

The line is cut into simple commands the way the shell runs them: at its operators, inside each
substitution — ``$( )``, backquotes, ``<( )`` —, inside the script of ``bash -c``, ``sh -c`` or
``zsh -c``, of ``eval``, of ``trap``, of ``env -S``, of ``su -c``, ``runuser -c``, ``flock -c``
and ``watch``; past the assignments and the prefixes that run a command (``sudo``, ``env``,
``timeout``, ``nohup``, ``xargs``, ``busybox``, ``chroot``, ``flock``…), whose long options take
their GNU abbreviations. Each command is then split into words by ``shlex``, and judged by the
base name of its command word. Comments, redirections and the body of a here-document run
nothing, and are left out — the body of an unquoted one is still searched for substitutions,
which the shell runs. ``shlex`` cuts the words alone: its operators do not tell a quoted ``;``
from one that ends a command, and ``kill 1 ';' $pid`` would hide its last target.

A ``cd`` into a directory of git is followed along the line, into the scripts it runs: the
relative paths that come after it are read from there. A ``cd`` to a literal path outside
``.git``, ``cd ..`` and ``cd -`` reset it. ``popd`` is not followed: after ``cd .git; popd`` the
state is kept, and ``rm foo.lock`` is refused although the shell may have left ``.git`` (the safe
side).

Out of scope, known limits: the ``cd`` is followed in the order of writing, whatever the ``&&``
and ``||`` between the commands (``cd .git && true || cd ..; rm x.lock`` passes); and a ``cd ..``
resets the state even from ``.git/refs/heads``, where the shell is still under ``.git``.
"""

import itertools
import json
import re
import shlex
import sys
from typing import TYPE_CHECKING, NamedTuple, cast

if TYPE_CHECKING:
    from collections.abc import Callable

RULE = (
    "An agent stops only what it started, by its PID or by a name of its own lot; never by "
    "pattern. A lock of git is not removed: the git command is run again."
)
INSTEAD = (
    "Instead: `kill <PID>` of a process you started; `docker rm`, `docker rmi` or `docker volume "
    "rm` of a literal name; for what the Makefile started, the target that stops it: "
    "`make test-services-down`, `make service-down`, `make e2e-down`, `make slot-release`; for a "
    "lock of git, the git command run again."
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
# What `docker` removes, by the group of its subcommand: `docker rmi`, `docker volume rm`…
_DOCKER_REMOVALS = {
    "": _CONTAINER_STOPS | {"rmi"},
    "container": _CONTAINER_STOPS,
    "image": frozenset({"rm", "remove"}),
    "volume": frozenset({"rm", "remove"}),
}
_COMPOSE_STOPS = frozenset({"down", "stop", "kill", "rm"})
# `kill -1` or `kill -0` alone reads as a signal without a target, or as a target: refused.
_LONE_TARGETS = frozenset({"-1", "-0"})
# The actions of `find` that run a command on what it found, and the commands that remove.
_FIND_EXECS = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
_FIND_REMOVERS = frozenset({"rm", "unlink", "mv", "rename"}) | _SHELLS
_FIND_OPTIONS = frozenset({"-H", "-L", "-P"})


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
    """The short options that take an argument."""
    long: frozenset[str] = frozenset()
    """The long options that take an argument."""
    flags: frozenset[str] = frozenset()
    """The long options that take none: an abbreviation is unique among them and ``long``."""
    operands: int = 0
    chdir: frozenset[str] = frozenset()
    """The options whose argument is the directory the command runs in."""
    scripts: frozenset[str] = frozenset()
    """The options whose argument is a line of shell."""
    abbreviates: bool = True
    """GNU ``getopt_long`` takes a unique prefix of a long option; Go's ``pflag`` does not."""

    def skip(self, words: list[str], index: int) -> int:
        """Return the index of the word that follows the options and operands from ``index``."""
        return self.parse(words, index)[1] + self.operands

    def parse(self, words: list[str], index: int) -> tuple[list[tuple[str, str]], int]:
        """Return the options from ``index`` that take an argument, and the index past them.

        Each option comes with its argument, a long one by its full name; the index is that of
        the first operand.
        """
        taken: list[tuple[str, str]] = []
        while index < len(words):
            word = words[index]
            following = words[index + 1] if index + 1 < len(words) else ""
            if word == "--":
                index += 1
                break
            # `-` alone is an operand, as standard input.
            if word == "-" or not word.startswith("-"):
                break
            if word.startswith("--"):
                written, equals, value = word.partition("=")
                name = self._long(written)
                takes = name in self.long
                if equals or takes:
                    taken.append((name, value if equals else following))
                index += 2 if takes and not equals else 1
                continue
            # A cluster of short options: the first that takes an argument ends it, the rest of
            # the word being its argument, or the next word when it ends the cluster.
            cluster = word[1:]
            taking = next((at for at, char in enumerate(cluster) if char in self.short), None)
            if taking is not None:
                rest = cluster[taking + 1 :]
                taken.append((f"-{cluster[taking]}", rest or following))
            index += 2 if taking == len(cluster) - 1 else 1
        return taken, index

    def permuted(self, words: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
        """Return the options that take an argument wherever they stand, and the operands.

        ``getopt`` without ``+`` reads an option past an operand: ``su root -c 'make'``.
        """
        taken: list[tuple[str, str]] = []
        operands: list[str] = []
        index = 0
        while index < len(words):
            found, index = self.parse(words, index)
            taken += found
            if index < len(words) and (words[index] == "-" or not words[index].startswith("-")):
                operands.append(words[index])
                index += 1
        return taken, operands

    def _long(self, written: str) -> str:
        """Return the long option ``written`` names: itself, or the one it uniquely abbreviates."""
        known = self.long | self.flags
        if not self.abbreviates or written in known:
            return written
        matches = [option for option in known if option.startswith(written)]
        # An ambiguous one is an error of the command, which then runs nothing.
        return matches[0] if len(matches) == 1 else written


def _names(*names: str) -> frozenset[str]:
    return frozenset(f"--{name}" for name in names)


_HELP = _names("help", "version")
# The option of `env` whose argument is a command line, which it splits into words and runs
# before the words that follow its options.
_SPLIT_STRING = frozenset({"-S", "--split-string"})
# The commands that run the command that follows their options.
_PREFIXES = {
    "sudo": _Options(
        "CDghpRrTtUu",
        _names("auth-type", "chdir", "chroot", "close-from", "command-timeout", "group", "host")
        | _names("login-class", "other-user", "prompt", "role", "type", "user"),
        _HELP
        | _names("askpass", "background", "bell", "edit", "list", "login", "non-interactive")
        | _names("no-update", "preserve-env", "preserve-groups", "remove-timestamp")
        | _names("reset-timestamp", "set-home", "shell", "stdin", "validate"),
        chdir=frozenset({"-D", "--chdir"}),
    ),
    "doas": _Options("Cu"),
    "env": _Options(
        "CSafu",
        _names("argv0", "chdir", "file", "split-string", "unset"),
        _HELP
        | _names("block-signal", "debug", "default-signal", "ignore-environment")
        | _names("ignore-signal", "list-signal-handling", "null"),
        chdir=frozenset({"-C", "--chdir"}),
        scripts=_SPLIT_STRING,
    ),
    "nohup": _Options(flags=_HELP),
    "nice": _Options("n", _names("adjustment"), _HELP),
    "timeout": _Options(
        "ks",
        _names("kill-after", "signal"),
        _HELP | _names("foreground", "preserve-status", "verbose"),
        operands=1,
    ),
    "time": _Options(
        "fo",
        _names("format", "output"),
        _HELP | _names("append", "portability", "quiet", "verbose"),
    ),
    "command": _Options(),
    "builtin": _Options(),
    "exec": _Options("a"),
    "setsid": _Options(flags=_HELP | _names("ctty", "fork", "wait")),
    "stdbuf": _Options("eio", _names("error", "input", "output"), _HELP),
    "ionice": _Options(
        "cn", _names("class", "classdata", "pgid", "pid", "uid"), _HELP | _names("ignore")
    ),
    "xargs": _Options(
        "EILPadns",
        _names("arg-file", "delimiter", "max-args", "max-chars", "max-procs", "process-slot-var"),
        _HELP
        | _names("eof", "exit", "interactive", "max-lines", "no-run-if-empty", "null")
        | _names("open-tty", "replace", "show-limits", "verbose"),
    ),
    # Its first operand is the applet, which stands as the command word.
    "busybox": _Options(flags=_HELP | _names("install", "list", "list-full")),
    # Its operand is the new root, where the command runs.
    "chroot": _Options("", _names("groups", "userspec"), _HELP | _names("skip-chdir"), operands=1),
    # Its operand is the lock; a `-c` after it brings a script instead of a command.
    "flock": _Options(
        "Ecw",
        _names("command", "conflict-exit-code", "timeout", "wait"),
        _HELP
        | _names("close", "exclusive", "fcntl", "nb", "no-fork", "nonblock", "nonblocking")
        | _names("shared", "unlock", "verbose"),
        operands=1,
        scripts=frozenset({"-c", "--command"}),
    ),
}
_SU = _Options(
    "Gcgsw",
    _names("command", "group", "session-command", "shell", "supp-group", "whitelist-environment"),
    _HELP | _names("fast", "login", "no-pty", "preserve-environment", "pty"),
    scripts=frozenset({"-c", "--command", "--session-command"}),
)
# `runuser -u <user> [--] <command>` runs the command itself, without a shell.
_RUNUSER = _SU._replace(short=_SU.short + "u", long=_SU.long | _names("user"))
_WATCH = _Options(
    "nq",
    _names("equexit", "interval"),
    _HELP
    | _names("beep", "chgexit", "color", "differences", "errexit", "exec", "no-color")
    | _names("no-rerun", "no-title", "no-wrap", "precise"),
)
# The long options of `bash` that take the next word for their argument.
_SHELL_LONG = frozenset({"--init-file", "--rcfile"})
_DOCKER = _Options(
    "cHl",
    _names("config", "context", "host", "log-level", "tlscacert", "tlscert", "tlskey"),
    abbreviates=False,
)
_TRAP = _Options()
_COMPOSE = _Options(
    "fp",
    _names("ansi", "env-file", "file", "parallel", "profile", "progress", "project-directory")
    | _names("project-name"),
    abbreviates=False,
)
# `docker-compose` (v1) is Python's argparse, which takes a unique prefix; `docker compose` is Go.
_COMPOSE_V1 = _COMPOSE._replace(abbreviates=True)


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


def _line(text: str, depth: int, *, piped: bool = False, moved: bool = False) -> str | None:
    return _judge(text, depth, piped=piped, moved=moved)[0]


def _judge(
    text: str, depth: int, *, piped: bool = False, moved: bool = False
) -> tuple[str | None, bool]:
    """Return the refused form a line takes, and whether it ends in a directory of git.

    ``moved``: the line runs after a ``cd`` into a directory of git.
    """
    commands: list[str] = []
    try:
        _Scanner(text, commands, depth).scan()
        split = [shlex.split(command) for command in commands]
    except ValueError:
        found = _FORBIDDEN.search(text)
        form = None if found is None else f"a line it cannot cut, which names `{found.group()}`"
        return form, moved
    for words in split:
        form, moved = _simple(words, depth, piped=piped, moved=moved)
        if form is not None:
            return form, moved
    return None, moved


def _simple(
    words: list[str], depth: int, *, piped: bool = False, moved: bool = False
) -> tuple[str | None, bool]:
    """Judge a simple command, past its assignments and the prefixes that run it.

    Return the refused form, and whether the shell stands in a directory of git after it.
    """
    # Where the command runs: a prefix may change it, for the command alone.
    here = moved
    index = 0
    while index < len(words):
        word = words[index]
        name = word.rsplit("/", 1)[-1]
        if _ASSIGNMENT.match(word) or word in _KEYWORDS:
            index += 1
            continue
        prefix = _PREFIXES.get(name)
        if prefix is None:
            arguments = words[index + 1 :]
            if name in {"cd", "pushd"}:
                return None, _cd(arguments, moved=here, pushd=name == "pushd")
            # `eval` runs in the shell itself: its `cd` holds for what follows it.
            if name == "eval":
                return _judge(" ".join(arguments), depth + 1, moved=here)
            check = _CHECKS.get(name)
            command = _Command(name, arguments, piped=piped, depth=depth, moved=here)
            return (None if check is None else check(command)), moved
        # What `xargs` runs takes its arguments from the pipe: they are never literal.
        piped = piped or name == "xargs"
        options, index = prefix.parse(words, index + 1)
        operands = words[index : index + prefix.operands]
        index += prefix.operands
        for option, value in options:
            if option in prefix.chdir:
                here = _moved(value, moved=here)
        if name == "chroot" and operands:
            here = _moved(operands[0], moved=here)
        scripts = [value for option, value in options if option in prefix.scripts]
        if name == "flock" and words[index : index + 1] in (["-c"], ["--command"]):
            scripts.append(words[index + 1] if index + 1 < len(words) else "")
            index = len(words)
        if name == "env" and scripts:
            # `env -S 'pkill x'`: the words of the line come before those that follow.
            line = " ".join([*scripts, shlex.join(words[index:])])
            return _line(line, depth + 1, piped=piped, moved=here), moved
        for script in scripts:
            if (form := _line(script, depth + 1, piped=piped, moved=here)) is not None:
                return form, moved
    return None, moved


def _cd(arguments: list[str], *, moved: bool, pushd: bool) -> bool:
    """Return whether the shell stands in a directory of git after ``cd`` or ``pushd``.

    ``pushd`` alone, or with ``+N`` or ``-N``, turns its stack: where it lands is not known, and
    the state is kept.
    """
    operands = list(arguments)
    while operands[:1] and operands[0].startswith("-") and operands[0] != "-":
        if operands.pop(0) == "--":
            break
    if not operands:
        return moved if pushd else False
    return _moved(operands[0], moved=moved)


def _moved(path: str, *, moved: bool) -> bool:
    """Return whether a change of directory to ``path`` leaves the shell in a directory of git.

    A path computed by a substitution or a variable is taken for ``git rev-parse --git-dir``; a
    relative path that does not climb keeps the state it starts from.

    Limit: any ``..`` first component resets the state, as the criterion asks, even when the
    shell is still under ``.git``: ``cd .git/refs/heads; cd ..; rm main.lock`` passes.
    """
    if "$" in path or ".git" in path.split("/"):
        return True
    if path in {"", "-"} or path.startswith(("/", "~")) or path.partition("/")[0] == "..":
        return False
    return moved


class _Command(NamedTuple):
    """A simple command to judge: the base name of its command word, and its arguments."""

    name: str
    arguments: list[str]
    piped: bool
    """Run by ``xargs``: its arguments come from a pipe."""
    depth: int
    moved: bool = False
    """Run in a directory of git, after a ``cd`` on the same line or by an option of a prefix."""


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
    # `docker container stop` is `docker stop`; `docker image rm`, `docker rmi`.
    group = words[0] if words[0] in _DOCKER_REMOVALS else ""
    if group:
        words = words[_DOCKER.skip(words, 1) :]
        if not words:
            return None
    verb, rest = words[0], words[1:]
    if "prune" in {verb, *rest[:1]}:
        return "`docker … prune`: it removes what the other lots hold"
    if verb in _DOCKER_REMOVALS[group]:
        return _container_stop(f"{group} {verb}".lstrip(), rest, piped=command.piped)
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
    index = (_COMPOSE_V1 if command.name == "docker-compose" else _COMPOSE).skip(arguments, 0)
    if index < len(arguments) and arguments[index] in _COMPOSE_STOPS:
        return (
            f"`{command.name} {arguments[index]}` outside the Makefile: the Makefile alone stops "
            "a platform, under the project name of its lot"
        )
    return None


def _unlink(command: _Command) -> str | None:
    """Refuse to remove or move a lock of git: ``rm``, ``unlink``, ``mv``, ``rename``."""
    for argument in command.arguments:
        directories, _, last = argument.rstrip("/").rpartition("/")
        lock = last.endswith(".lock")
        in_git = ".git" in directories.split("/") or (command.moved and lock)
        # A directory computed by a substitution or a variable is `git rev-parse --git-dir`.
        if (in_git and (lock or last[-1:] in {"*", "?", "]"})) or (lock and "$" in directories):
            return (
                f"`{command.name} {argument}`: a lock of git is held by a git command that runs, "
                "maybe in another worktree"
            )
    return None


def _find(command: _Command) -> str | None:
    """Judge a ``find`` that removes what it finds, by ``-delete`` or ``-exec rm``.

    It is refused in a directory of git, or when it looks for a lock: from the root of a clone,
    ``find . -name '*.lock' -delete`` reaches the locks of ``.git``.
    """
    arguments = command.arguments
    index = 0
    while index < len(arguments) and (
        arguments[index] in _FIND_OPTIONS or arguments[index][:2] in {"-D", "-O"}
    ):
        index += 2 if arguments[index] == "-D" else 1
    paths: list[str] = []
    while index < len(arguments) and arguments[index][:1] not in {"-", "(", ")", "!"}:
        paths.append(arguments[index])
        index += 1
    expression = arguments[index:]
    removes = "-delete" in expression or any(
        word in _FIND_EXECS and following.rsplit("/", 1)[-1] in _FIND_REMOVERS
        for word, following in itertools.pairwise(expression)
    )
    in_git = command.moved or any(".git" in path.split("/") for path in paths)
    names_lock = any(".lock" in word for word in expression)
    if removes and (in_git or names_lock):
        reason = "the expression names a .lock" if names_lock and not in_git else "it is in git"
        return (
            f"`find … -delete` or `-exec rm` ({reason}): a lock of git is held by a git "
            "command that runs, maybe in another worktree"
        )
    return None


def _shell(command: _Command) -> str | None:
    """Judge the script of ``bash -c``, ``sh -c`` and their like; a script file is not read.

    ``bash`` and ``dash`` take the argument of each ``-o`` or ``-O`` of a cluster from the words
    that follow it, ``zsh`` from the rest of the cluster when the ``-o`` does not end it: the
    script is judged under both readings.
    """
    arguments = command.arguments
    scripts = {_script(arguments, rest=rest) for rest in (False, True)}
    return next(
        (
            form
            for script in sorted(found for found in scripts if found is not None)
            if (form := _line(arguments[script], command.depth + 1, moved=command.moved))
            is not None
        ),
        None,
    )


def _script(arguments: list[str], *, rest: bool) -> int | None:
    """Return the index of the script of a shell run with ``-c``, or None when there is none.

    ``rest``: an ``-o`` that does not end its cluster takes the rest of it for its argument;
    otherwise each ``-o`` of a cluster takes the next word.
    """
    index = 0
    scripted = False
    while index < len(arguments):
        word = arguments[index]
        if word in {"-", "--"}:
            index += 1
            break
        if word[:1] not in {"-", "+"} or word in {"-", "+"}:
            break
        index += 1
        if word.startswith("--"):
            index += 1 if word in _SHELL_LONG else 0
            continue
        cluster = word[1:]
        for at, char in enumerate(cluster):
            if char in "oO" and rest:
                index += 1 if at == len(cluster) - 1 else 0
                break
            if char in "oO":
                index += 1
            # `bash` and `dash` read a `c` of `+c` as one of `-c`.
            scripted = scripted or char == "c"
    return index if scripted and index < len(arguments) else None


def _su(command: _Command) -> str | None:
    """Judge the script of ``su -c`` or ``runuser -c``, and the command of ``runuser -u``.

    Their options are read wherever they stand, as ``getopt`` permutes them; the words that
    follow the user are passed to the shell, which reads a ``-c`` among them too.
    """
    table = _RUNUSER if command.name == "runuser" else _SU
    arguments = command.arguments
    options, operands = table.permuted(arguments)
    if command.name == "runuser":
        # After `-u <user>` nothing is permuted: all that follows is the command, `kill -1` too.
        first, index = table.parse(arguments, 0)
        if any(option in {"-u", "--user"} for option, _ in first):
            options, operands = first, arguments[index:]
    for option, script in options:
        if option in table.scripts and (
            form := _line(script, command.depth + 1, moved=command.moved)
        ):
            return form
    if any(option in {"-u", "--user"} for option, _ in options):
        return _simple(operands, command.depth + 1, piped=command.piped, moved=command.moved)[0]
    return None


def _watch(command: _Command) -> str | None:
    """Judge what ``watch`` runs: its operands, joined, are the script of ``sh -c``."""
    index = _WATCH.skip(command.arguments, 0)
    script = " ".join(command.arguments[index:])
    return _line(script, command.depth + 1, piped=command.piped, moved=command.moved)


def _trap(command: _Command) -> str | None:
    """Judge the action of ``trap``, which the shell runs on its signal: ``trap 'kill 0' EXIT``."""
    arguments = command.arguments[_TRAP.skip(command.arguments, 0) :]
    return _line(arguments[0], command.depth + 1, moved=command.moved) if arguments else None


_CHECKS: dict[str, Callable[[_Command], str | None]] = {
    "pkill": _pattern,
    "killall": _pattern,
    "fuser": _fuser,
    "kill": _kill,
    "docker": _docker,
    "docker-compose": _compose,
    "rm": _unlink,
    "unlink": _unlink,
    "mv": _unlink,
    "rename": _unlink,
    "find": _find,
    "su": _su,
    "runuser": _su,
    "watch": _watch,
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
