# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The guard of the commands of the agents: no agent stops what another started (US-1080).

Each form the criteria and the design of US-1080 refuse has its case, and each form they let
pass: ``pkill`` and ``killall``, a ``kill`` of a target that is no PID, run by ``xargs`` or of
every process, a ``docker`` stop of computed targets, ``docker … prune``, ``docker compose …
down`` outside the Makefile, the removal of a lock of git — wherever the command stands in the
line. The hook that runs the guard is declared in ``.claude/settings.json``, and is tried as
Claude Code runs it.
"""

import ast
import io
import json
import os
import subprocess
import sys

import pytest

from wftools import REPOSITORY, guard

GUARD = REPOSITORY / "tools" / "src" / "wftools" / "guard.py"
SETTINGS = REPOSITORY / ".claude" / "settings.json"
HOOK = 'python3 "$CLAUDE_PROJECT_DIR/tools/src/wftools/guard.py"'


def refused(command: str) -> bool:
    return guard.refusal(command) is not None


@pytest.mark.parametrize(
    "command",
    [
        'pkill -f "^make check"',
        "killall make",
        "/usr/bin/pkill -f vitest",
        "fuser -k 3000/tcp",
    ],
)
def test_a_stop_by_pattern_is_refused(command: str) -> None:
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "kill $(pgrep make)",
        "kill `pgrep make`",
        "kill $pid",
        'kill "$(cat server.pid)"',
        "kill make",
        "kill %1",
        "kill -9 12345 vitest",
    ],
)
def test_a_kill_of_a_target_that_is_no_pid_is_refused(command: str) -> None:
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "pgrep make | xargs kill",
        "pgrep -f vitest | xargs -r kill -9",
        "pgrep make | xargs -I{} kill {}",
        "pgrep make | xargs -n 1 sudo kill",
    ],
)
def test_a_kill_run_by_xargs_is_refused(command: str) -> None:
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    ["kill -1", "kill -9 -1", "kill -- -1", "kill 0", "kill -TERM 0", "kill -0", "kill -- -0"],
)
def test_a_kill_of_every_process_of_the_user_or_of_its_group_is_refused(command: str) -> None:
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "kill 12345",
        "kill -TERM 12345 12346",
        "kill -s TERM 12345",
        "kill -- -12345",
        "kill -9 -12345",
        "kill -0 12345",
        "kill 12345 2>/dev/null || true",
        "kill -l",
    ],
)
def test_a_kill_of_a_pid_or_of_the_group_of_a_process_passes(command: str) -> None:
    assert not refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "docker rm -f $(docker ps -q)",
        "docker stop `docker ps -q`",
        'docker kill "$container"',
        "docker ps -q | xargs docker stop",
        "docker ps -aq | xargs -r docker rm -f",
        "docker ps -q | xargs docker kill",
        "docker stop --filter name=wf",
        "docker rm -f --filter=label=wf",
        "docker rm -f wf-*",
        "docker stop wf-s?-pg",
        "docker container stop $(docker ps -q)",
        "docker container -D stop $(docker ps -q)",
        "docker container rm -f wf-*",
        "docker ps -q | xargs docker container kill",
        "docker restart $(docker ps -q)",
    ],
)
def test_a_docker_stop_of_computed_targets_is_refused(command: str) -> None:
    assert refused(command)


@pytest.mark.parametrize(
    "objects", ["system", "container", "volume", "image", "network", "builder", "buildx"]
)
def test_a_docker_prune_is_refused_whatever_its_object(objects: str) -> None:
    assert refused(f"docker {objects} prune -f")


@pytest.mark.parametrize(
    "command",
    [
        "docker compose down",
        "docker compose -f deploy/compose/compose.yaml -p wf-slot-1 down -v",
        "docker compose --project-name waterfall stop",
        "docker compose kill api",
        "docker compose rm -f api",
        "docker-compose down",
        "docker-compose -p waterfall stop",
        "docker --context default compose down",
    ],
)
def test_a_docker_compose_stop_outside_the_makefile_is_refused(command: str) -> None:
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "rm -f .git/index.lock",
        "rm .git/refs/heads/lot/US-1080.lock",
        "unlink .git/worktrees/agent-1/index.lock",
        "rm -f /home/agent/wf-project/.git/packed-refs.lock",
        'rm -f "$(git rev-parse --git-dir)/index.lock"',
        "rm -f $GIT_DIR/HEAD.lock",
        "rm -f .git/*.lock",
        "cd .git && rm index.lock",
        "cd .git; rm -f *.lock",
        "rm -f x/.git/index.lock/",
    ],
)
def test_the_removal_of_a_lock_of_git_is_refused(command: str) -> None:
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "true; pkill x",
        "true && pkill x",
        "false || pkill x",
        "ps aux | pkill x",
        "make test &\npkill x",
        "cd /tmp\npkill x",
        "echo $(pkill x)",
        'echo "$(pkill x)"',
        "echo `pkill x`",
        "echo $(echo $(pkill x))",
        "diff <(pkill x) /dev/null",
        "ls > $(pkill x)",
        "(pkill x)",
        "{ pkill x; }",
        "if true; then pkill x; fi",
        "bash -c 'pkill x'",
        'sh -c "pkill x"',
        "zsh -c 'pkill x'",
        "bash -lc 'pkill x'",
        "bash -o pipefail -c 'true | pkill x'",
        "bash -c 'bash -c \"pkill x\"'",
        "eval 'pkill x'",
        "trap 'kill 0' EXIT; make e2e",
        "sudo pkill x",
        "sudo -u root -- pkill x",
        "env pkill x",
        "env -i PATH=/usr/bin pkill x",
        "timeout 10 pkill x",
        "timeout -s KILL 5s pkill x",
        "nohup pkill x &",
        "nice pkill x",
        "nice -n 10 pkill x",
        "time pkill x",
        "command pkill x",
        "exec pkill x",
        "WATERFALL_SLOT=1 pkill x",
        "\\pkill x",
        "ls # a comment\npkill x",
        "cat <<EOF\n$(pkill x)\nEOF",
        "cat <<'EOF'\nthe body\nEOF\npkill x",
    ],
)
def test_the_refusal_holds_wherever_the_command_stands(command: str) -> None:
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "env -S 'pkill x'",
        "env --split-string='kill $pid'",
        '/usr/bin/env -S "docker stop $(docker ps -q)"',
        "env -S'pkill x'",
        "env -iS 'pkill x'",
        "env --split-string 'pkill x'",
        "env --sp 'pkill x'",
        "env -S kill '$pid'",
        "env -S 'env -S \"pkill x\"'",
        "pgrep make | xargs env -S kill",
    ],
)
def test_the_line_that_env_splits_is_judged_as_a_line(command: str) -> None:
    assert refused(command)


def test_a_permitted_line_that_env_splits_passes() -> None:
    assert not refused("env -S 'kill 12345'")
    assert not refused("env -S 'make check' BASE=origin/epic/EP-19")


@pytest.mark.parametrize(
    "command",
    [
        "bash -euo pipefail -c 'pkill x'",
        "bash -eo pipefail -c 'pkill x'",
        "sh -o errexit -c 'kill $pid'",
        "zsh -o pipefail -ec 'pkill x'",
        "bash -oe pipefail -c 'pkill x'",
        "bash -co pipefail 'pkill x'",
        "bash +o posix -O extglob -c 'pkill x'",
        "zsh -opipefail -c 'pkill x'",
        "bash --rcfile /dev/null -c 'pkill x'",
        "bash -c -- 'pkill x'",
    ],
)
def test_the_script_of_a_shell_is_found_past_its_options(command: str) -> None:
    assert refused(command)


def test_a_permitted_script_past_the_options_of_a_shell_passes() -> None:
    assert not refused("bash -euo pipefail -c 'kill 12345'")
    assert not refused("bash -euo pipefail scripts/run.sh pkill")


def test_a_line_not_cut_is_refused_when_it_names_a_forbidden_word() -> None:
    assert refused('echo "never closed; pkill x')
    assert refused("rm -f '.git/index.lock")
    assert not refused('echo "never closed')


def test_a_line_nested_beyond_measure_is_judged_as_one_not_cut() -> None:
    deep = "true"
    for _ in range(40):
        deep = f"echo $({deep})"
    assert not refused(deep)
    assert refused(deep.replace("true", "pkill x"))


@pytest.mark.parametrize(
    "command",
    [
        "docker rm -f wf-s3-pg",
        "docker stop wf-s3-pg",
        "docker stop 3f2a9c1b7d4e",
        "docker stop -t 5 wf-s3-pg wf-s3-redis",
        "docker container stop wf-s3-pg",
        "docker container -D stop wf-s3-pg",
        "cd /tmp && rm foo.lock",
        "docker ps -q --filter name=wf-s3",
        "docker compose ps",
        "docker compose -p wf-slot-1 up -d",
        "docker compose run --rm api pytest",
        "git worktree prune",
        "make test-services-down",
        "make service-down",
        "make check BASE=origin/epic/EP-19 > /tmp/check.log 2>&1; tail -n 60 /tmp/check.log",
        "rm -f tools/uv.lock",
        "rm -rf frontend/.next",
        "pgrep -f vitest",
        "ps aux | grep make",
        "grep -rn pkill docs/dev",
        'git commit -m "Refuse pkill and kill $(…) to the agents"',
        "echo '$(pkill x)'",
        "ls # pkill x",
        "trap 'rm -rf build' EXIT",
        "git commit -F - <<'EOF'\nRefuse pkill; l'arrêt par motif\nkill $pid\nEOF",
        "gh pr create --body \"$(cat <<'EOF'\nl'arrêt par motif : pkill\nEOF\n)\"",
    ],
)
def test_a_command_that_stops_nothing_of_another_passes(command: str) -> None:
    assert not refused(command)


def run(event: str, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(event))
    return guard.main()


def test_the_refusal_says_the_rule_the_form_and_what_to_do_instead(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "kill $(pgrep make)"}})
    assert run(event, monkeypatch) == 2
    said = capsys.readouterr()
    assert said.out == ""
    assert "`kill $(…)`" in said.err
    assert "by its PID or by a name of its own lot; never by pattern" in said.err
    assert "A lock of git is not removed: the git command is run again" in said.err
    instead = ("kill <PID>", "make test-services-down", "make service-down", "make slot-release")
    assert all(command in said.err for command in instead)


@pytest.mark.parametrize(
    "event",
    [
        json.dumps({"tool_name": "Bash", "tool_input": {"command": "make check"}}),
        "not JSON",
        json.dumps(["pkill x"]),
        json.dumps({"tool_name": "Bash"}),
        json.dumps({"tool_input": {"command": ["pkill", "x"]}}),
    ],
)
def test_a_command_permitted_or_an_event_not_read_passes_in_silence(
    event: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(event, monkeypatch) == 0
    assert capsys.readouterr() == ("", "")


def test_the_hook_is_declared_for_the_bash_tool() -> None:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    [entry] = settings["hooks"]["PreToolUse"]
    assert entry["matcher"] == "Bash"
    assert entry["hooks"] == [{"type": "command", "command": HOOK}]


@pytest.mark.parametrize(("command", "code"), [("pkill -f make", 2), ("make check", 0)])
def test_the_hook_runs_the_guard_as_claude_code_does(command: str, code: int) -> None:
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    environment = {**os.environ, "CLAUDE_PROJECT_DIR": str(REPOSITORY)}
    ran = subprocess.run(
        ["bash", "-c", HOOK],
        input=event,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == code
    assert ("`pkill`" in ran.stderr) == (code == 2)


def test_the_guard_imports_the_standard_library_alone() -> None:
    nodes = list(ast.walk(ast.parse(GUARD.read_text(encoding="utf-8"))))
    imports = [node for node in nodes if isinstance(node, ast.Import)]
    imported = {alias.name for node in imports for alias in node.names}
    imported |= {node.module or "" for node in nodes if isinstance(node, ast.ImportFrom)}
    assert imported
    assert {name.split(".")[0] for name in imported} <= sys.stdlib_module_names
