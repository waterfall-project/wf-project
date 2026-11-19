# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The options of the commands the command guard reads past (US-1080, US-1310, US-2450).

``guard.py`` judges a simple command past the prefixes that run another command — ``sudo``,
``env``, ``xargs``, ``uv run``, ``npx``… — and reads the operands of ``make``, ``docker``, ``su``
or ``watch``: this module holds the options of each, and the parser that skips them. Like the
guard, it depends on the standard library alone: the hook runs the guard, and the guard this
module, before the environment of the tools is synchronised.
"""

from typing import NamedTuple


class Options(NamedTuple):
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
    versions: bool = False
    """The command it runs is that of a package, whose version it may pin: ``kill-port@1``."""

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
PREFIXES = {
    "sudo": Options(
        "CDghpRrTtUu",
        _names("auth-type", "chdir", "chroot", "close-from", "command-timeout", "group", "host")
        | _names("login-class", "other-user", "prompt", "role", "type", "user"),
        _HELP
        | _names("askpass", "background", "bell", "edit", "list", "login", "non-interactive")
        | _names("no-update", "preserve-env", "preserve-groups", "remove-timestamp")
        | _names("reset-timestamp", "set-home", "shell", "stdin", "validate"),
        chdir=frozenset({"-D", "--chdir"}),
    ),
    "doas": Options("Cu"),
    "env": Options(
        "CSafu",
        _names("argv0", "chdir", "file", "split-string", "unset"),
        _HELP
        | _names("block-signal", "debug", "default-signal", "ignore-environment")
        | _names("ignore-signal", "list-signal-handling", "null"),
        chdir=frozenset({"-C", "--chdir"}),
        scripts=_SPLIT_STRING,
    ),
    "nohup": Options(flags=_HELP),
    "nice": Options("n", _names("adjustment"), _HELP),
    "timeout": Options(
        "ks",
        _names("kill-after", "signal"),
        _HELP | _names("foreground", "preserve-status", "verbose"),
        operands=1,
    ),
    "time": Options(
        "fo",
        _names("format", "output"),
        _HELP | _names("append", "portability", "quiet", "verbose"),
    ),
    "command": Options(),
    "builtin": Options(),
    "exec": Options("a"),
    "setsid": Options(flags=_HELP | _names("ctty", "fork", "wait")),
    "stdbuf": Options("eio", _names("error", "input", "output"), _HELP),
    "ionice": Options(
        "cn", _names("class", "classdata", "pgid", "pid", "uid"), _HELP | _names("ignore")
    ),
    "xargs": Options(
        "EILPadns",
        _names("arg-file", "delimiter", "max-args", "max-chars", "max-procs", "process-slot-var"),
        _HELP
        | _names("eof", "exit", "interactive", "max-lines", "no-run-if-empty", "null")
        | _names("open-tty", "replace", "show-limits", "verbose"),
    ),
    # Its first operand is the applet, which stands as the command word.
    "busybox": Options(flags=_HELP | _names("install", "list", "list-full")),
    # Its operand is the new root, where the command runs.
    "chroot": Options("", _names("groups", "userspec"), _HELP | _names("skip-chdir"), operands=1),
    # Its operand is the lock; a `-c` after it brings a script instead of a command.
    "flock": Options(
        "Ecw",
        _names("command", "conflict-exit-code", "timeout", "wait"),
        _HELP
        | _names("close", "exclusive", "fcntl", "nb", "no-fork", "nonblock", "nonblocking")
        | _names("shared", "unlock", "verbose"),
        operands=1,
        scripts=frozenset({"-c", "--command"}),
    ),
}
# `npx` and `npm exec` run a command of a package, `-c` a line of shell (US-2450).
_NPM_EXEC = Options(
    "cpw",
    _names("cache", "call", "package", "prefix", "registry", "userconfig", "workspace"),
    _HELP | _names("include-workspace-root", "no", "quiet", "workspaces", "yes"),
    scripts=frozenset({"-c", "--call"}),
    versions=True,
)
PREFIXES["npx"] = _NPM_EXEC
# `pnpm dlx` and `pnpm exec`: `-c` is a flag there, which runs the command by a shell; the word
# that follows is that command, judged as the script of `npx -c`.
_PNPM_EXEC = Options(
    "c",
    _names("allow-build", "package", "report-summary", "resume-from", "shell-mode"),
    _HELP | _names("no-reporter-hide-prefix", "parallel", "recursive", "silent"),
    scripts=frozenset({"-c", "--shell-mode"}),
    versions=True,
)
# `uv run` (clap, which takes no abbreviation): the options that take the next word.
_UV = _names("allow-insecure-host", "cache-dir", "color", "config-file", "directory", "project")
# `-m <module>` and `-s <script>` run Python with no word `python`: their operand is taken as the
# argument of the option, which `guard.py` judges as the module or the script of `python`.
UV_PYTHON = frozenset({"-m", "--module", "-s", "--script"})
UV_RUN = Options(
    "CPfimpsw",
    _UV
    | _names("module", "script")
    | _names("config-setting", "config-settings-package", "default-index", "env-file", "exclude")
    | _names("exclude-newer", "exclude-newer-package", "extra", "extra-index-url", "find-links")
    | _names("fork-strategy", "group", "index", "index-strategy", "index-url", "keyring-provider")
    | _names("link-mode", "no-binary-package", "no-build-isolation-package", "no-build-package")
    | _names("no-extra", "upgrade-group", "no-editable-package", "prerelease-package")
    | _names("no-sources-package")
    | _names("no-group", "only-group", "package", "prerelease", "python", "python-platform")
    | _names("python-preference", "refresh-package", "reinstall-package", "resolution")
    | _names("upgrade-package", "with", "with-editable", "with-requirements"),
    abbreviates=False,
    chdir=_names("directory"),
)
# The commands that run another past a subcommand: their options, then the options of each
# subcommand that runs one (US-2450): `uv run pkill`, `pnpm dlx kill-port`.
LAUNCHERS = {
    "uv": (Options("", _UV, abbreviates=False, chdir=_names("directory")), {"run": UV_RUN}),
    "npm": (Options("w", _names("prefix", "userconfig", "workspace")), {"exec": _NPM_EXEC}),
    "pnpm": (
        Options(
            "CF",
            _names("dir", "filter", "filter-prod", "loglevel", "reporter"),
            chdir=frozenset({"-C", "--dir"}),
        ),
        {"dlx": _PNPM_EXEC, "exec": _PNPM_EXEC},
    ),
}
SU = Options(
    "Gcgsw",
    _names("command", "group", "session-command", "shell", "supp-group", "whitelist-environment"),
    _HELP | _names("fast", "login", "no-pty", "preserve-environment", "pty"),
    scripts=frozenset({"-c", "--command", "--session-command"}),
)
# `runuser -u <user> [--] <command>` runs the command itself, without a shell.
RUNUSER = SU._replace(short=SU.short + "u", long=SU.long | _names("user"))
WATCH = Options(
    "nq",
    _names("equexit", "interval"),
    _HELP
    | _names("beep", "chgexit", "color", "differences", "errexit", "exec", "no-color")
    | _names("no-rerun", "no-title", "no-wrap", "precise"),
)
# The long options of `bash` that take the next word for their argument.
SHELL_LONG = frozenset({"--init-file", "--rcfile"})
DOCKER = Options(
    "cHl",
    _names("config", "context", "host", "log-level", "tlscacert", "tlscert", "tlskey"),
    abbreviates=False,
)
TRAP = Options()
# The options of GNU `make` that take the next word; `-j`, `-l`, `-O` take theirs in the same word
# only, a `-j 2` making `2` an operand, which no target is named.
MAKE = Options(
    "CEfIoW",
    _names("assume-new", "assume-old", "directory", "eval", "file", "include-dir", "makefile")
    | _names("new-file", "old-file", "what-if"),
    _HELP
    | _names("always-make", "check-symlink-times", "debug", "dry-run", "environment-overrides")
    | _names("ignore-errors", "jobs", "just-print", "keep-going", "load-average", "max-load")
    | _names("no-builtin-rules", "no-builtin-variables", "no-keep-going", "no-print-directory")
    | _names("no-silent", "output-sync", "print-data-base", "print-directory", "question")
    | _names("quiet", "recon", "shuffle", "silent", "stop", "touch", "trace")
    | _names("warn-undefined-variables"),
)
COMPOSE = Options(
    "fp",
    _names("ansi", "env-file", "file", "parallel", "profile", "progress", "project-directory")
    | _names("project-name"),
    abbreviates=False,
)
# `docker-compose` (v1) is Python's argparse, which takes a unique prefix; `docker compose` is Go.
COMPOSE_V1 = COMPOSE._replace(abbreviates=True)
