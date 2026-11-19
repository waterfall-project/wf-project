# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Judge the forms of the command guard that reach ``.git`` and its locks (US-1310, US-2450).

``guard.py`` cuts the line into simple commands and judges each by its command word; this module
holds the judgement of those that may remove or move what git holds: ``rm``, ``unlink``, ``mv``,
``rename`` and ``truncate``, ``find`` with ``-delete`` or ``-exec rm``, and the ``cd`` that leaves
the shell in a directory of git. It holds too the simple command that every check of the guard
receives.

``rm``, ``unlink``, ``mv`` and ``truncate`` are refused an operand that is ``.git``, passes through
a ``.git/``, opens by ``.git`` and a joker (``.git*``) or is a pattern that matches ``.git``
(``.g*``, ``.{git,x}``), wherever it stands among the operands or in the value of an option
(US-2450, #2417). ``find`` is refused when a branch of its expression — what an ``-o`` at the top
separates — names ``.git`` and removes: ``find . -name .git -prune -exec rm -rf {} +``; the usual
``find . -name .git -prune -o -name '*.pyc' -delete`` passes, its removal in the other branch.

Like the guard, it depends on the standard library alone: the hook runs the guard, and the guard
this module, before the environment of the tools is synchronised.

A ``cd`` into a directory of git is followed along the line, into the scripts it runs: the
relative paths that come after it are read from there. A ``cd`` to a literal path outside
``.git``, ``cd ..`` and ``cd -`` reset it. ``popd`` is not followed: after ``cd .git; popd`` the
state is kept, and ``rm foo.lock`` is refused although the shell may have left ``.git`` (the safe
side).
"""

import fnmatch
import itertools
import re
from typing import NamedTuple

SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh", "ash", "rbash"})
# The actions of `find` that run a command on what it found, and the commands that remove.
_FIND_EXECS = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
_FIND_REMOVERS = frozenset({"rm", "unlink", "mv", "rename", "truncate"}) | SHELLS
_FIND_OPTIONS = frozenset({"-H", "-L", "-P"})
_FIND_OR = frozenset({"-o", "-or"})
# The commands refused an operand that reaches `.git`: `rename` takes an expression first, which
# names no file.
_GIT_OPERANDS = frozenset({"rm", "unlink", "mv", "truncate"})
_JOKERS = frozenset({"*", "?", "["})
# The short options whose argument may be written in the same word: `mv -t.git`, `truncate -r…`.
_ATTACHED = {"mv": "St", "truncate": "rs"}
# A group of braces, innermost; the shell expands it when it holds a comma.
_BRACES = re.compile(r"\{[^{}]*\}")
# A sequence of braces, `{a..z}` or `{1..9..2}`: of letters, it may make `.git` (`.{g..h}it`).
_SEQUENCE = re.compile(r"\{([^{}]|[-+]?\d+)\.\.([^{}]|[-+]?\d+)(?:\.\.[-+]?\d+)?\}")
# Past this many words, a brace expansion is not followed: the path is taken for one of `.git`.
_MAX_EXPANSIONS = 256
# Past this length a pattern is not matched, which would take a time of its square: it is taken
# for one of `.git`. No name of a file is longer.
_NAME_MAX = 255
_REPOSITORY = (
    "it removes or changes what git holds, the repository that every worktree shares, and the "
    "work of each"
)
_UNEVALUATED = (
    "the pattern may name `.git`, and the guard does not evaluate classes or sequences of "
    "braces: write the paths in clear"
)


class Command(NamedTuple):
    """A simple command to judge: the base name of its command word, and its arguments."""

    name: str
    arguments: list[str]
    piped: bool
    """Run by ``xargs``: its arguments come from a pipe."""
    depth: int
    moved: bool = False
    """Run in a directory of git, after a ``cd`` on the same line or by an option of a prefix."""
    named: bool = False
    """A command before it, or the directory it runs in, names a path of git or a lock."""
    fed: tuple[str, ...] = ()
    """What it reads on its input that the line writes: the body of a here-document, a
    here-string, what an ``echo`` or a ``printf`` before it in its pipeline writes."""


def names_git(words: list[str]) -> bool:
    """Say whether a command names a path of git or a lock: the source a pipe may feed to ``rm``."""
    return any(".lock" in word or ".git" in word.split("/") for word in words)


def cd(arguments: list[str], *, moved: bool, pushd: bool) -> bool:
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
    return into_git(operands[0], moved=moved)


def into_git(path: str, *, moved: bool) -> bool:
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


def reaches_git(path: str) -> bool:
    """Say whether a path is ``.git``, passes through ``.git/``, or opens by ``.git`` and a joker.

    ``.gitignore``, ``.github`` and ``.git-old`` do not; ``.git*`` and ``x/.git?/HEAD`` do, and so
    does a part whose pattern matches ``.git`` — ``.g*``, ``.[g]it``, ``.*`` —, and a path whose
    braces expand to one of them: ``.{git,x}``. A joker does not match the dot that opens a name.

    ``fnmatch`` knows neither the classes of POSIX nor the sequences of braces (#3792): a path that
    holds a class, ``.[[:alpha:]]it``, or a sequence of characters, ``.{g..h}it``, is taken for one
    of ``.git`` without looking, like a pattern too long to match. A sequence of numbers makes
    neither a dot nor a letter: ``log{1..3}`` passes.
    """
    if _unevaluated(path):
        return True
    expanded = _expand(path)
    return expanded is None or any(
        _git_part(part) for written in expanded for part in written.split("/")
    )


def _unevaluated(path: str) -> bool:
    """Say whether ``path`` holds a class of POSIX or a sequence of characters, never evaluated."""
    return "[:" in path or any(
        not (first.lstrip("+-").isdigit() and last.lstrip("+-").isdigit())
        for first, last in _SEQUENCE.findall(path)
    )


def _git_part(part: str) -> bool:
    if part == ".git" or (part.startswith(".git") and part[4:5] in _JOKERS):
        return True
    if part[:1] != "." or not _JOKERS & set(part):
        return False
    return len(part) > _NAME_MAX or fnmatch.fnmatchcase(".git", part.replace("[^", "[!"))


def _expand(path: str) -> list[str] | None:
    """Return the words the braces of ``path`` expand to; None past ``_MAX_EXPANSIONS``."""
    pending = [path]
    done: list[str] = []
    while pending:
        word = pending.pop()
        group = next((found for found in _BRACES.finditer(word) if "," in found.group()), None)
        if group is None:
            done.append(word)
            continue
        head, tail = word[: group.start()], word[group.end() :]
        pending += [head + choice + tail for choice in group.group()[1:-1].split(",")]
        if len(pending) + len(done) > _MAX_EXPANSIONS:
            return None
    return done


def unlink(command: Command) -> str | None:
    """Refuse to remove, move or truncate a lock of git, or what ``.git`` holds.

    ``rm``, ``unlink``, ``mv``, ``rename`` and ``truncate``.
    """
    if command.piped and command.named:
        return (
            f"`{command.name}` run by `xargs` on what a command that names .git or a .lock "
            "found: a lock of git is held by a git command that runs, maybe in another worktree"
        )
    if command.name == "rm" and _recursive(command.arguments):
        for argument in command.arguments:
            if argument.rstrip("/").rpartition("/")[2] == ".git":
                return (
                    f"`rm -r {argument}`: it removes the repository, and the work of every worktree"
                )
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
    if command.name in _GIT_OPERANDS:
        for operand in _operands(command.name, command.arguments):
            if reaches_git(operand):
                why = _UNEVALUATED if _unevaluated(operand) else _REPOSITORY
                return f"`{command.name} {operand}`: {why}"
    return None


def _operands(name: str, arguments: list[str]) -> list[str]:
    """Return the paths a command names: its operands, all past ``--``, and the paths of options.

    The value of a long option after ``=`` is judged as a path, ``mv --target-directory=.git``,
    and so is the argument written in the word of a short one that takes it, ``mv -t.git``.
    """
    paths: list[str] = []
    attached = _ATTACHED.get(name, "")
    for at, word in enumerate(arguments):
        if word == "--":
            return paths + arguments[at + 1 :]
        if word.startswith("--"):
            paths += [word.partition("=")[2]] if "=" in word else []
        elif word[:1] == "-":
            cluster = word[1:]
            taking = next((place for place, char in enumerate(cluster) if char in attached), None)
            paths += [cluster[taking + 1 :]] if taking is not None and cluster[taking + 1 :] else []
        else:
            paths.append(word)
    return paths


def _recursive(arguments: list[str]) -> bool:
    """Say whether the options of an ``rm`` ask for a recursive removal."""
    for word in arguments:
        if word == "--":
            return False
        if word == "--recursive" or (
            word[:1] == "-" and word[1:2] != "-" and set(word) & set("rR")
        ):
            return True
    return False


def find(command: Command) -> str | None:
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
    removes = _removes(expression)
    in_git = command.moved or any(".git" in path.split("/") for path in paths)
    names_lock = any(".lock" in word for word in expression)
    if removes and (in_git or names_lock):
        reason = "the expression names a .lock" if names_lock and not in_git else "it is in git"
        return (
            f"`find … -delete` or `-exec rm` ({reason}): a lock of git is held by a git "
            "command that runs, maybe in another worktree"
        )
    if any(_removes(branch) and any(map(reaches_git, branch)) for branch in _branches(expression)):
        return f"`find … -name .git` with `-delete` or `-exec rm`: {_REPOSITORY}"
    return None


def _removes(expression: list[str]) -> bool:
    """Say whether an expression of ``find`` removes what it finds: ``-delete``, ``-exec rm``."""
    return "-delete" in expression or any(
        word in _FIND_EXECS and following.rsplit("/", 1)[-1] in _FIND_REMOVERS
        for word, following in itertools.pairwise(expression)
    )


def _branches(expression: list[str]) -> list[list[str]]:
    """Cut an expression of ``find`` at each ``-o`` outside parentheses.

    A branch runs its actions on what its own tests matched: past an ``-o``, a ``-name .git
    -prune`` no longer holds. The words of an ``-exec`` stand in the branch, as they come.
    """
    branches: list[list[str]] = [[]]
    nesting = 0
    for word in expression:
        nesting += {"(": 1, ")": -1}.get(word, 0)
        if word in _FIND_OR and nesting == 0:
            branches.append([])
        else:
            branches[-1].append(word)
    return branches
