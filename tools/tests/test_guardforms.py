# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The forms written in clear that the command guard refuses since US-2450/L3 (#3715, #3792).

What a shell reads on its input is judged as its script: the body of a here-document given to
``bash``, ``sh`` or ``zsh``, a here-string, and the literal text an ``echo`` or a ``printf`` sends
it by a pipe. ``kill-port`` is refused, alone or run by ``npx`` and ``pnpm dlx``; ``uv run`` is a
prefix, as ``env``; ``gmake`` is ``make``; ``python -m wftools.mergequeue create`` is ``make
merge-queue``. A POSIX class or a sequence of braces in a path is taken for ``.git``. Each form
has its case, and the neighbouring commands that stay legitimate pass. The guard is a tool of
the repository: no test cites a requirement (WF-QUA-0010).
"""

import pytest

from wftools import guard

STOP = "`pkill`: it stops processes by a pattern"


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "bash <<'EOF'\npkill -f make\nEOF",
        "bash <<EOF\nls\npkill -f make\nEOF",
        "sh -s <<EOF\npkill -f make\nEOF",
        "sh -s -- a b <<'EOF'\npkill -f make\nEOF",
        "zsh <<-'EOF'\n\tpkill -f make\n\tEOF",
        "bash <<-EOF\n\tpkill -f make\nEOF",
        "sudo bash <<'EOF'\npkill -f make\nEOF",
        "bash <<'EOF' > out.log\nif true; then\n  pkill -f make\nfi\nEOF",
        "ls; bash <<'EOF'\npkill -f make\nEOF\necho done",
        "bash <<< 'pkill -f make'",
        "cat <<'EOF' | bash\npkill -f make\nEOF",
    ],
)
def test_a_here_document_given_to_a_shell_is_judged_as_its_script(command: str) -> None:
    """PLC-07: a `pkill` in the body of a here-document that `bash`, `sh` or `zsh` reads."""
    assert guard.refusal(command) == STOP


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "echo 'pkill -f make' | bash",
        'echo "pkill -f make" | sh',
        "echo pkill -f make | zsh",
        "echo -n 'pkill -f make' | bash",
        "printf 'pkill -f make\\n' | bash",
        "printf '%s\\n' 'pkill -f make' | sh -s",
        "printf 'ls\\npkill -f make\\n' | bash",
        "echo 'pkill -f make' | sudo bash",
        "echo 'pkill -f make' | tee run.log | bash",
        "echo 'cd .git && rm index.lock' | bash",
    ],
)
def test_what_echo_or_printf_pipes_to_a_shell_is_judged_as_its_script(command: str) -> None:
    """PLC-07: the literal argument of an `echo` or a `printf` whose pipe ends in a shell."""
    assert guard.refusal(command) is not None


@pytest.mark.story("US-2450")
def test_the_arguments_of_echo_are_judged_joined_as_the_shell_reads_them() -> None:
    """PLC-07: `echo kill 0` writes one command, `kill 0`, which no argument alone makes."""
    said = guard.refusal("echo kill 0 | bash")
    assert said is not None
    assert said.startswith("`kill 0`")


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "cat <<'EOF'\npkill -f make\nEOF",
        "git commit -F - <<'EOF'\npkill -f make\nEOF",
        "cat > notes.md <<'EOF'\npkill -f make\nEOF",
        "echo 'pkill -f make'",
        "echo 'pkill -f make' > notes.md",
        "echo 'pkill -f make'; bash -c 'ls'",
        "echo 'pkill -f make' | grep pkill",
        "bash -c 'cat' <<'EOF'\npkill -f make\nEOF",
        "echo 'pkill -f make' | bash -c 'cat > notes.md'",
        "bash <<'EOF'\nmake check\nEOF",
        "echo 'make check' | bash",
    ],
)
def test_the_text_no_shell_reads_as_its_script_passes(command: str) -> None:
    """PLC-07: a body or an `echo` that no shell reads, or a shell run with `-c`, runs nothing."""
    assert guard.refusal(command) is None


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "kill-port 3000",
        "npx kill-port 3000",
        "npx --yes kill-port 3000 5173",
        "npx -p kill-port kill-port 3000",
        "npx -c 'kill-port 3000'",
        "npm exec -- kill-port 3000",
        "pnpm dlx kill-port 3000",
        "pnpm --dir frontend dlx kill-port 3000",
        "pnpm exec kill-port 3000",
        "/usr/local/bin/kill-port 3000",
        "npx kill-port 3000 'open",
    ],
)
def test_kill_port_is_refused_alone_and_behind_npx_or_pnpm_dlx(command: str) -> None:
    """PLC-07: `kill-port` stops whatever holds a port, alone or run by `npx` or `pnpm dlx`."""
    said = guard.refusal(command)
    assert said is not None
    assert "kill-port" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "uv run pkill -f make",
        "uv run -- pkill -f make",
        "uv run --frozen --project tools pkill -f make",
        "uv run --with requests --group dev pkill -f make",
        "uv --directory tools run pkill -f make",
        "uv run env pkill -f make",
        "uv run bash -c 'pkill -f make'",
    ],
)
def test_uv_run_is_a_prefix_as_env(command: str) -> None:
    """PLC-07: what `uv run` runs is judged as what `env` runs, past its options."""
    assert guard.refusal(command) == STOP


@pytest.mark.story("US-2450")
def test_uv_run_follows_its_directory_into_git() -> None:
    """PLC-07: `uv run --directory .git` runs in `.git`, where a lock is not removed."""
    said = guard.refusal("uv run --directory .git rm index.lock")
    assert said is not None
    assert "a lock of git" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "gmake merge-queue",
        "gmake merge-queue EPIC=EP-28",
        "gmake -j2 merge-queue EPIC=EP-28",
        "/usr/bin/gmake -s merge-queue",
        "uv run gmake merge-queue",
        "gmake merge-queue EPIC=EP-28 'open",
    ],
)
def test_gmake_merge_queue_is_refused_as_make_merge_queue(command: str) -> None:
    """PLC-07: `gmake` is GNU `make`: its target `merge-queue` is refused."""
    said = guard.refusal(command)
    assert said is not None
    assert "merge-queue" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "python -m wftools.mergequeue create EP-28",
        "python3 -m wftools.mergequeue create EP-28",
        "python3.14 -I -m wftools.mergequeue create EP-28",
        "python3 -Im wftools.mergequeue create EP-28",
        "python -mwftools.mergequeue create EP-28",
        "python -W ignore -m wftools.mergequeue create EP-28",
        "python tools/src/wftools/mergequeue.py create EP-28",
        "uv run python -m wftools.mergequeue create EP-28",
        "uv run --frozen --project tools python -m wftools.mergequeue create EP-28",
        "cd tools && uv run python -m wftools.mergequeue create EP-28",
        "python -m wftools.mergequeue create EP-28 'open",
    ],
)
def test_the_merge_queue_created_by_python_is_refused_under_uv_run_or_not(command: str) -> None:
    """PLC-07: `python -m wftools.mergequeue create` is what `make merge-queue` runs."""
    said = guard.refusal(command)
    assert said is not None
    assert "mergequeue create" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest",
        "uv run --frozen pytest -n 4 --dist worksteal tests/test_guard.py",
        "uv run --frozen --project tools --group workflows actionlint",
        "uv run --frozen --project tools python -m wftools.mergequeue check EP-28",
        "python -m wftools.mergequeue check EP-28",
        "python -m wftools.tracking create",
        "python -c 'import wftools.mergequeue' create",
        "uv sync --frozen",
        "gmake check",
        "gmake merge-queue-check EPIC=EP-28",
        "npx playwright test",
        "npm exec -- prettier --check .",
        "pnpm dlx prettier --check .",
        "pnpm install --frozen-lockfile",
        "command -v kill-port",
    ],
)
def test_the_neighbours_of_the_launchers_pass(command: str) -> None:
    """PLC-07: the tests, the check of the merge queue and the other targets still run."""
    assert guard.refusal(command) is None


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "operand",
    [".[[:alpha:]]it", ".[[:lower:]]it", ".{g..h}it", ".{a..z}it", "{-..0}git", "x/.{f..h}it/HEAD"],
)
def test_a_posix_class_or_a_sequence_of_braces_is_taken_for_git(operand: str) -> None:
    """#3792: `fnmatch` knows neither: the guard refuses without looking, as past its bounds."""
    said = guard.refusal(f"rm -rf {operand}")
    assert said is not None
    assert "the repository that every worktree shares" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize("command", ["rm -f log{1..3}.txt", "rm -rf build/{01..12}"])
def test_a_sequence_of_numbers_passes(command: str) -> None:
    """#3792: a sequence of numbers makes neither a dot nor a letter."""
    assert guard.refusal(command) is None
