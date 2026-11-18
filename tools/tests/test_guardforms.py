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

import re
import shutil
import subprocess

import pytest

from wftools import guard, guardoptions

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
        "npx kill-port@latest 3000",
        "npx -y kill-port@2.0.1 3000",
        "npx --yes @scope/kill-port@1 3000",
        "pnpm dlx kill-port@latest 3000",
        "npm exec kill-port@1 3000",
        "npm exec -- kill-port@1 3000",
    ],
)
def test_kill_port_is_refused_alone_and_behind_npx_or_pnpm_dlx(command: str) -> None:
    """PLC-07: `kill-port` stops whatever holds a port, alone or run by `npx` or `pnpm dlx`.

    Its version pinned too, the usual form of `npx`.
    """
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
        "python -- tools/src/wftools/mergequeue.py create EP-28",
        "uv run python -m wftools.mergequeue create EP-28",
        "uv run --frozen --project tools python -m wftools.mergequeue create EP-28",
        "cd tools && uv run python -m wftools.mergequeue create EP-28",
        "python -m wftools.mergequeue create EP-28 'open",
        "uv run -m wftools.mergequeue create EP-28",
        "uv run --module wftools.mergequeue create",
        "uv run --frozen -m wftools.mergequeue create EP-28",
        "uv run -s tools/src/wftools/mergequeue.py create EP-28",
        "uv run --script tools/src/wftools/mergequeue.py create EP-28",
        "uv run tools/src/wftools/mergequeue.py create EP-28",
    ],
)
def test_the_merge_queue_created_by_python_is_refused_under_uv_run_or_not(command: str) -> None:
    """PLC-07: `python -m wftools.mergequeue create` is what `make merge-queue` runs.

    `uv run -m` and `uv run -s` run the module or the script with no word `python`.
    """
    said = guard.refusal(command)
    assert said is not None
    assert "mergequeue create" in said


@pytest.mark.story("US-2500")
@pytest.mark.parametrize(
    "command",
    [
        "uv run -m foo -m wftools.mergequeue create EP-28",
        "uv run -m wftools.mergequeue create EP-28 -m foo",
        "uv run -m foo --module wftools.mergequeue create EP-28",
        "uv run -m foo -s tools/src/wftools/mergequeue.py create EP-28",
        "uv run -s foo.py -m wftools.mergequeue create EP-28",
    ],
)
def test_each_module_or_script_of_uv_run_is_judged_not_only_the_first(command: str) -> None:
    """[US-2500] #3796: uv keeps the last `-m` or `-s`, and `uv run -m foo -m …` was let through."""
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
        "uv run -m wftools.mergequeue check EP-28",
        "uv run -m pytest tests/test_guard.py",
        "uv run tools/src/wftools/mergequeue.py check EP-28",
        "timeout -s KILL 5 make check",
        "python -m wftools.tracking create",
        "python -c 'import wftools.mergequeue' create",
        "uv sync --frozen",
        "gmake check",
        "gmake merge-queue-check EPIC=EP-28",
        "npx playwright test",
        "npx playwright@1.50 test",
        "npx @playwright/test@1.50 --version",
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
    assert "write the paths in clear" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize("command", ["rm -f log{1..3}.txt", "rm -rf build/{01..12}"])
def test_a_sequence_of_numbers_passes(command: str) -> None:
    """#3792: a sequence of numbers makes neither a dot nor a letter."""
    assert guard.refusal(command) is None


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "option",
    [
        "--no-extra",
        "--upgrade-group",
        "--no-editable-package",
        "--prerelease-package",
        "--no-sources-package",
    ],
)
def test_the_options_of_uv_run_that_take_a_value_do_not_hide_the_command(option: str) -> None:
    """PLC-07: the value of `--no-extra` is no command: `pkill` that follows it is judged."""
    assert guard.refusal(f"uv run {option} x pkill -f make") == STOP


@pytest.mark.story("US-2450")
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is absent")
def test_the_table_of_uv_run_holds_the_options_its_help_says_take_a_value() -> None:
    """PLC-07: every `--option <VALUE>` of `uv run --help` is in the table of the guard."""
    text = subprocess.run(
        ["uv", "run", "--help"], capture_output=True, text=True, check=False
    ).stdout
    found = set(re.findall(r"(--[a-z][a-z-]*) <", text))
    assert found
    assert found <= guardoptions.UV_RUN.long


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "pnpm exec -c 'pkill x'",
        "pnpm dlx --shell-mode 'pkill x'",
        "pnpm dlx -c 'pkill x'",
        "npm -w x exec pkill y",
        "npm -w x exec -- pkill y",
    ],
)
def test_pnpm_shell_mode_and_npm_workspace_are_followed(command: str) -> None:
    """PLC-07: `pnpm exec -c` runs a line of shell; `npm -w <ws>` takes its value."""
    said = guard.refusal(command)
    assert said is not None
    assert "pkill" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "echo 'pkill x' | bash script.sh",
        "bash script.sh <<< 'pkill'",
        "bash script.sh <<EOF\npkill x\nEOF",
        "echo 'pkill x' | bash -x -- script.sh",
    ],
)
def test_a_shell_with_a_script_file_does_not_read_its_input(command: str) -> None:
    """PLC-07: with an operand and no `-s`, the text given to the shell is not its script."""
    assert guard.refusal(command) is None


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "echo 'pkill x' | bash -n",
        "echo 'pkill x' | bash -s script.sh",
        "echo 'pkill x' | ash",
        "echo 'pkill x' | rbash",
    ],
)
def test_a_shell_that_reads_its_input_is_still_judged(command: str) -> None:
    """PLC-07: `bash -n` and `-s` read the input; `ash` and `rbash` are shells."""
    assert guard.refusal(command) == STOP


@pytest.mark.story("US-2450")
def test_a_sequence_of_braces_is_refused_with_its_own_message() -> None:
    """#3792: the guard does not evaluate the pattern, and says so, not that it names git."""
    said = guard.refusal("rm -rf out/{a..c}")
    assert said is not None
    assert "every worktree shares" not in said
    assert "write the paths in clear" in said
