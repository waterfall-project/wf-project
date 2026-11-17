# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Refuse a command of an agent that would stop what another agent started (US-1080, US-1310).

The ``PreToolUse`` hook of ``.claude/settings.json`` runs it before every command of the ``Bash``
tool, through the launcher: ``python3 "$CLAUDE_PROJECT_DIR/tools/src/wftools/launch.py" guard ||
exit 2``. It reads the JSON of the hook on its input and refuses by the code 2, the reason on its
error output; otherwise it says nothing and returns 0. Claude Code lets a command pass on any other
code: the launcher, and the hook past it, turn a failure of the guard, or a Python older than 3.14,
into a refusal (US-2450); a JSON the guard cannot read lets the command pass.

It depends on the standard library alone and on two modules beside it: ``guardgit.py``, which
judges the forms that reach ``.git`` and its locks, and ``guardoptions.py``, the options of the
commands it reads past. A fresh worktree runs it before its environment is synchronised, by its
path, outside the package, and finds those modules in its own directory.

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

Three more forms are refused (US-1340): ``xargs rm`` (or ``unlink``, ``mv``, ``rename``) when a
command before it in its pipeline names ``.git`` or a lock (US-2450: ``find .git; ls | xargs rm``
passes), ``rm -r`` of ``.git``, and the target ``merge-queue`` of ``make``, which a person alone
runs, wherever it stands among the options of ``make`` (US-2450: in ``make -C merge-queue``, it is
a directory). ``command -v`` looks a name up and runs nothing: the name that follows is not judged.

A ``cd`` into a directory of git is followed along the line, into the scripts it runs
(``guardgit.py``).

Out of scope, known limits: the ``cd`` is followed in the order of writing, whatever the ``&&``
and ``||`` between the commands (``cd .git && true || cd ..; rm x.lock`` passes); and a ``cd ..``
resets the state even from ``.git/refs/heads``, where the shell is still under ``.git``.
"""

import json
import re
import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, cast

# The type checker reads the package; the launcher runs this file by its path, outside the
# package: the modules beside it are imported from its directory, put first, before any other.
if TYPE_CHECKING or __package__:
    from wftools import guardgit, guardoptions
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import guardgit
    import guardoptions

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
# A word of shell, its quoted parts holding blanks, that runs over no other `make`: the search,
# which tries each `make` of the line, then reads each character once (`make -C make -C …`).
_FREE = r"(?!(?<![\w-])make\s)"
_WORD = rf"""(?:'(?:{_FREE}[^'])*+'|"(?:{_FREE}[^"])*+"|(?:{_FREE}[^\s'"])++)++"""
# What a line not cut is refused for naming: the command words of the forms refused. Between
# `make` and `merge-queue` stand its options, its assignments, a number of `-j 2` and quoted words;
# an option that takes the next word for its argument takes it, once (`make -C merge-queue`
# passes). Each element is atomic, and none opens by a blank. Limit: a quoted word that holds
# `make ` ends the options (`make -f 'a make b' merge-queue 'x` passes); the shell, which does
# not run a line with an open quote, runs none of them.
_FORBIDDEN = re.compile(
    r"(?<![\w-])(?:pkill|killall|kill|docker|docker-compose)(?![\w-])|\.lock\b"
    rf"|(?<![\w-])make(?:\s+(?>-[CEfIoW]\s+{_WORD}|-{_WORD}|[A-Za-z_]\w*\+?=(?:{_WORD})?"
    rf"""|[0-9.]+|(?=['"]){_WORD}))*+"""
    r"\s+merge-queue(?![\w-])"
)
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
_PID = re.compile(r"-?[0-9]+")
_KEYWORDS = frozenset({"!", "{", "if", "then", "else", "elif", "do", "while", "until"})
# The words that open a group of commands, and those that close it, as the first of a command.
_GROUPS: dict[str, int] = {
    **dict.fromkeys(("{", "if", "while", "until", "for", "case", "select"), 1),
    **dict.fromkeys(("}", "fi", "done", "esac"), -1),
}
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


class _UnsplittableError(ValueError):
    """A line the guard cannot cut: an open quote or substitution, or one nested too deep."""


class _Heredoc(NamedTuple):
    """A here-document whose body follows the line that opens it."""

    delimiter: str
    tabs: bool
    expands: bool


class _Scanner:
    """Cut a text of shell into its simple commands, appended to a list as their raw words.

    A substitution is cut in turn, its commands appended to the same list, and stands as
    ``$(…)`` in the word that holds it.

    Each command comes with the number of its pipeline, which a ``;``, an ``&``, an ``&&``, an
    ``||`` or a newline ends; ``|`` and ``|&`` do not, nor the newlines and comments that follow
    them before the next command. A group — ``( )``, ``{ }``, ``if … fi``, a
    loop, ``case … esac`` — is one element of the pipeline that holds it: what it writes may feed
    a pipe after it, and the separators inside it end nothing. The commands of a substitution
    belong to the pipeline of the command that holds it, whose argument they make.
    """

    def __init__(
        self, text: str, commands: list[tuple[str, int]], depth: int, root: _Scanner | None = None
    ) -> None:
        if depth > _MAX_DEPTH:
            raise _UnsplittableError
        self.text = text
        self.commands = commands
        self.depth = depth
        self.position = 0
        self.heredocs: list[_Heredoc] = []
        # The scanner of the line counts its pipelines and its groups; those of its
        # substitutions number their commands by it.
        self.root = self if root is None else root
        self.pipeline = 0
        self.groups = 0
        # A `|` or `|&` was read, and no word since.
        self.piping = False

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
                ends = _ends_pipeline(text, self.position) and not (char == "\n" and self.piping)
                if self.root is self and nesting == 0 and self.groups == 0:
                    self.pipeline += ends
                # `a |⏎ b` is one pipeline: a newline, or a comment, after a pipe ends nothing.
                self.piping = _pipes(text, self.position) or (self.piping and char in "&\n")
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
                self.piping = False
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
            self.commands.append((" ".join(words), self.root.pipeline))
            self.groups = max(self.groups + _GROUPS.get(words[0], 0), 0)
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
        nested = _Scanner(self.text, self.commands, self.depth + 1, self.root)
        return nested.scan(start, closing=True)

    def _backquoted(self, start: int) -> int:
        text = self.text
        index = start
        while index < len(text):
            if text[index] == "\\":
                index += 2
            elif text[index] == "`":
                inner = _BACKSLASHED.sub(r"\1", text[start:index])
                _Scanner(inner, self.commands, self.depth + 1, self.root).scan()
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


def _pipes(text: str, index: int) -> bool:
    """Say whether the operator at ``index`` is a ``|`` that pipes: neither ``||`` nor a half."""
    return text[index] == "|" and not _ends_pipeline(text, index)


def _ends_pipeline(text: str, index: int) -> bool:
    """Say whether the operator at ``index`` ends a pipeline: neither ``|`` nor ``|&`` does."""
    char = text[index]
    if char == "|":
        return text.startswith("||", index) or text[index - 1 : index] == "|"
    if char == "&":
        return text[index - 1 : index] != "|"
    return char in ";\n"


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
    commands: list[tuple[str, int]] = []
    try:
        _Scanner(text, commands, depth).scan()
        split = [(shlex.split(command), pipeline) for command, pipeline in commands]
    except ValueError:
        found = _FORBIDDEN.search(text)
        form = None if found is None else f"a line it cannot cut, which names `{found.group()}`"
        return form, moved
    # What a command of the pipeline before it named feeds no `xargs rm` of this one.
    named = False
    previous = 0
    for words, pipeline in split:
        named = named and pipeline == previous
        previous = pipeline
        form, moved = _simple(words, depth, piped=piped, moved=moved, named=named or moved)
        if form is not None:
            return form, moved
        named = named or guardgit.names_git(words)
    return None, moved


def _simple(
    words: list[str], depth: int, *, piped: bool = False, moved: bool = False, named: bool = False
) -> tuple[str | None, bool]:
    """Judge a simple command, past its assignments and the prefixes that run it.

    Return the refused form, and whether the shell stands in a directory of git after it.
    ``named``: a command before it on the line names a path of git or a lock.
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
        if name == "command" and _describes(words[index + 1 :]):
            # `command -v pkill` looks a name up: nothing is run.
            break
        prefix = guardoptions.PREFIXES.get(name)
        if prefix is None:
            arguments = words[index + 1 :]
            if name in {"cd", "pushd"}:
                return None, guardgit.cd(arguments, moved=here, pushd=name == "pushd")
            # `eval` runs in the shell itself: its `cd` holds for what follows it.
            if name == "eval":
                return _judge(" ".join(arguments), depth + 1, moved=here)
            check = _CHECKS.get(name)
            command = guardgit.Command(
                name, arguments, piped=piped, depth=depth, moved=here, named=named
            )
            return (None if check is None else check(command)), moved
        # What `xargs` runs takes its arguments from the pipe: they are never literal.
        piped = piped or name == "xargs"
        options, index = prefix.parse(words, index + 1)
        operands = words[index : index + prefix.operands]
        index += prefix.operands
        for option, value in options:
            if option in prefix.chdir:
                here = guardgit.into_git(value, moved=here)
        if name == "chroot" and operands:
            here = guardgit.into_git(operands[0], moved=here)
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


def _describes(arguments: list[str]) -> bool:
    """Say whether ``command`` looks a name up (``-v``, ``-V``, ``-pv``) instead of running it."""
    for word in arguments:
        if word == "--" or word[:1] != "-" or word == "-":
            return False
        if set(word[1:]) <= set("pvV") and set(word[1:]) & set("vV"):
            return True
        if set(word[1:]) != {"p"}:
            return False
    return False


def _pattern(command: guardgit.Command) -> str | None:
    return f"`{command.name}`: it stops processes by a pattern"


def _fuser(command: guardgit.Command) -> str | None:
    killing = any(
        word == "--kill" or (word[:1] == "-" and word[1:2] != "-" and "k" in word[1:])
        for word in command.arguments
    )
    return "`fuser -k`: it stops the processes that hold a file or a port" if killing else None


def _kill(command: guardgit.Command) -> str | None:
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


def _docker(command: guardgit.Command) -> str | None:
    words = command.arguments[guardoptions.DOCKER.skip(command.arguments, 0) :]
    if not words:
        return None
    if words[0] == "compose":
        return _compose(command._replace(name="docker compose", arguments=words[1:]))
    # `docker container stop` is `docker stop`; `docker image rm`, `docker rmi`.
    group = words[0] if words[0] in _DOCKER_REMOVALS else ""
    if group:
        words = words[guardoptions.DOCKER.skip(words, 1) :]
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


def _compose(command: guardgit.Command) -> str | None:
    arguments = command.arguments
    index = (
        guardoptions.COMPOSE_V1 if command.name == "docker-compose" else guardoptions.COMPOSE
    ).skip(arguments, 0)
    if index < len(arguments) and arguments[index] in _COMPOSE_STOPS:
        return (
            f"`{command.name} {arguments[index]}` outside the Makefile: the Makefile alone stops "
            "a platform, under the project name of its lot"
        )
    return None


def _make(command: guardgit.Command) -> str | None:
    """Refuse the target ``merge-queue``, which a person runs; ``merge-queue-check`` passes.

    A target is an operand that is no assignment, wherever it stands among the options, which
    GNU ``make`` permutes: in ``make -C merge-queue check``, ``merge-queue`` is a directory.
    """
    _, operands = guardoptions.MAKE.permuted(command.arguments)
    if "merge-queue" in operands:
        return (
            "`make merge-queue`: it creates the rule set of the merge queue with the token of the "
            "user; a person runs it, and `make merge-queue-check` says whether it is there"
        )
    return None


def _shell(command: guardgit.Command) -> str | None:
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
            index += 1 if word in guardoptions.SHELL_LONG else 0
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


def _su(command: guardgit.Command) -> str | None:
    """Judge the script of ``su -c`` or ``runuser -c``, and the command of ``runuser -u``.

    Their options are read wherever they stand, as ``getopt`` permutes them; the words that
    follow the user are passed to the shell, which reads a ``-c`` among them too.
    """
    table = guardoptions.RUNUSER if command.name == "runuser" else guardoptions.SU
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


def _watch(command: guardgit.Command) -> str | None:
    """Judge what ``watch`` runs: its operands, joined, are the script of ``sh -c``."""
    index = guardoptions.WATCH.skip(command.arguments, 0)
    script = " ".join(command.arguments[index:])
    return _line(script, command.depth + 1, piped=command.piped, moved=command.moved)


def _trap(command: guardgit.Command) -> str | None:
    """Judge the action of ``trap``, which the shell runs on its signal: ``trap 'kill 0' EXIT``."""
    arguments = command.arguments[guardoptions.TRAP.skip(command.arguments, 0) :]
    return _line(arguments[0], command.depth + 1, moved=command.moved) if arguments else None


_CHECKS: dict[str, Callable[[guardgit.Command], str | None]] = {
    "pkill": _pattern,
    "killall": _pattern,
    "fuser": _fuser,
    "kill": _kill,
    "docker": _docker,
    "docker-compose": _compose,
    "rm": guardgit.unlink,
    "unlink": guardgit.unlink,
    "mv": guardgit.unlink,
    "rename": guardgit.unlink,
    "truncate": guardgit.unlink,
    "find": guardgit.find,
    "make": _make,
    "su": _su,
    "runuser": _su,
    "watch": _watch,
    "trap": _trap,
} | dict.fromkeys(guardgit.SHELLS, _shell)


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
