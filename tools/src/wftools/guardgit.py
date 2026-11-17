# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Judge the forms of the command guard that reach ``.git`` and its locks (US-1310, US-2450).

``guard.py`` cuts the line into simple commands and judges each by its command word; this module
holds the judgement of those that may remove or move what git holds: ``rm``, ``unlink``, ``mv``,
``rename`` and ``truncate``, ``find`` with ``-delete`` or ``-exec rm``, and the ``cd`` that leaves
the shell in a directory of git. It holds too the simple command that every check of the guard
receives.

``rm``, ``unlink``, ``mv`` and ``truncate`` are refused an operand that is ``.git``, passes through
a ``.git/`` or opens by ``.git`` and a joker (``.git*``), wherever it stands among the operands
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

import itertools
from typing import NamedTuple

SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
# The actions of `find` that run a command on what it found, and the commands that remove.
_FIND_EXECS = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
_FIND_REMOVERS = frozenset({"rm", "unlink", "mv", "rename"}) | SHELLS
_FIND_OPTIONS = frozenset({"-H", "-L", "-P"})
_FIND_OR = frozenset({"-o", "-or"})
# The commands refused an operand that reaches `.git`: `rename` takes an expression first, which
# names no file.
_GIT_OPERANDS = frozenset({"rm", "unlink", "mv", "truncate"})
_JOKERS = frozenset({"*", "?", "["})
_REPOSITORY = (
    "it removes or changes what git holds, the repository that every worktree shares, and the "
    "work of each"
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

    ``.gitignore``, ``.github`` and ``.git-old`` do not; ``.git*`` and ``x/.git?/HEAD`` do.
    """
    return any(
        part == ".git" or (part.startswith(".git") and part[4:5] in _JOKERS)
        for part in path.split("/")
    )


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
        for operand in _operands(command.arguments):
            if reaches_git(operand):
                return f"`{command.name} {operand}`: {_REPOSITORY}"
    return None


def _operands(arguments: list[str]) -> list[str]:
    """Return the operands of a command: the words that are no option, and all past ``--``."""
    if "--" not in arguments:
        return [word for word in arguments if word[:1] != "-"]
    end = arguments.index("--")
    return [word for word in arguments[:end] if word[:1] != "-"] + arguments[end + 1 :]


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
