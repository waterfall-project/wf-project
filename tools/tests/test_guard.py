# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The guard of the commands of the agents: no agent stops what another started (US-1080).

Each form the criteria and the design of US-1080 refuse has its case, and each form they let
pass: ``pkill`` and ``killall``, a ``kill`` of a target that is no PID, run by ``xargs`` or of
every process, a ``docker`` stop of computed targets, ``docker … prune``, ``docker compose …
down`` outside the Makefile, the removal of a lock of git — wherever the command stands in the
line. The hook that runs the guard is declared in ``.claude/settings.json``, and is tried as
Claude Code runs it.

US-1310 adds the forms an agent writes without malice (#1890, #1893): each of its criteria is
named by the docstring of the tests that hold it. The guard is a tool of the repository: no test
cites a requirement (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
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
        "docker-compose --project-n waterfall down",
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
    instead = (
        "kill <PID>",
        "make test-services-down",
        "make service-down",
        "make e2e-down",
        "make slot-release",
    )
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
    """US-1310: the guard stays a script of the standard library, under 1,000 lines."""
    text = GUARD.read_text(encoding="utf-8")
    nodes = list(ast.walk(ast.parse(text)))
    imports = [node for node in nodes if isinstance(node, ast.Import)]
    imported = {alias.name for node in imports for alias in node.names}
    imported |= {node.module or "" for node in nodes if isinstance(node, ast.ImportFrom)}
    assert imported
    assert {name.split(".")[0] for name in imported} <= sys.stdlib_module_names
    assert len(text.splitlines()) <= 1000


@pytest.mark.parametrize(
    "command",
    [
        "find .git -name '*.lock' -delete",
        "find .git -name '*.lock' -exec rm -f {} +",
        "find -L .git/refs -name '*.lock' -execdir /bin/rm {} ';'",
        "find .git/ -name index.lock -exec sh -c 'rm \"$1\"' _ {} ';'",
        "find . -name '*.lock' -delete",
        'find "$(git rev-parse --git-dir)" -name index.lock -delete',
        "cd .git && find . -type f -newer HEAD -delete",
        "mv .git/index.lock /tmp/index.lock.old",
        "mv -f .git/refs/heads/main.lock /tmp",
        'mv "$(git rev-parse --git-dir)/index.lock" /tmp',
        "cd .git && mv index.lock index.lock.bak",
        "rename .lock .old .git/index.lock",
    ],
)
def test_a_lock_of_git_neither_found_and_removed_nor_moved(command: str) -> None:
    """US-1310: `find` through `.git` with `-delete` or `-exec rm`, `mv` or `rename` of a lock."""
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "find .git -name '*.lock'",
        "find .git -name '*.lock' -exec ls -l {} +",
        "find frontend -name '*.tsbuildinfo' -delete",
        "find . -name __pycache__ -exec rm -rf {} +",
        "mv tools/uv.lock /tmp/uv.lock",
        "mv build/a.txt build/b.txt",
        "rename .txt .md notes/a.txt",
        "cd .git; cd ..; mv foo.lock bar.lock",
    ],
)
def test_a_find_or_a_move_outside_the_locks_of_git_passes(command: str) -> None:
    """US-1310: the forms next to those refused, which touch no lock of git."""
    assert not refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "docker rmi $(docker images -q)",
        "docker rmi -f wf-*",
        "docker images -q | xargs docker rmi",
        "docker image rm $(docker images -q)",
        "docker image remove --filter dangling=true",
        "docker volume rm $(docker volume ls -q)",
        "docker volume remove wf-s?_pg",
        "docker volume ls -q | xargs -r docker volume rm",
        "docker volume rm --filter=label=wf",
        'docker volume rm "wf-$SLOT_pg"',
        "docker image prune -a",
    ],
)
def test_a_docker_removal_of_images_or_volumes_computed_is_refused(command: str) -> None:
    """US-1310: `docker rmi`, `docker image rm|remove`, `docker volume rm|remove` as `docker rm`."""
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "docker rmi waterfall-front:test",
        "docker image rm 3f2a9c1b7d4e",
        "docker image remove waterfall-back:lot",
        "docker volume rm wf-s3_pgdata",
        "docker volume remove wf-s3_pgdata wf-s3_redis",
        "docker volume ls --filter name=wf",
        "docker image ls",
    ],
)
def test_a_docker_removal_of_a_literal_image_or_volume_passes(command: str) -> None:
    """US-1310: a literal target of `docker rmi` or `docker volume rm` passes."""
    assert not refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "flock /tmp/x pkill make",
        "flock -w 10 /tmp/x pkill make",
        "flock --timeout 10 -n /tmp/x kill $pid",
        "flock -E 3 /tmp/x -c 'pkill make'",
        "flock /tmp/x --command 'pkill make'",
        "su -c 'pkill make'",
        "su - root -c 'pkill make'",
        "su -s /bin/bash -c 'kill $pid' bob",
        "su root -- -c 'pkill make'",
        "su --command='pkill make'",
        "su -lc 'pkill make'",
        "runuser -u bob -- pkill make",
        "runuser -u bob kill $pid",
        "runuser -u bob kill -1",
        "runuser -u bob kill 0",
        "runuser --user bob kill -1",
        "runuser -l bob -c 'pkill make'",
        "busybox pkill make",
        "busybox kill $(pidof make)",
        "chroot / pkill make",
        "chroot --userspec bob:bob / pkill make",
        "watch 'pkill make'",
        "watch -n 5 pkill make",
        "watch --interval 5 'kill $pid'",
        "watch -x kill $pid",
        "sudo flock /tmp/x busybox pkill make",
    ],
)
def test_the_command_a_new_prefix_runs_is_judged(command: str) -> None:
    """US-1310: `busybox`, `su -c`, `runuser -c`, `flock`, `watch` and `chroot`, with options."""
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "flock /tmp/x make check",
        "flock -w 10 /tmp/x -c 'kill 12345'",
        "su -c 'make check' bob",
        "runuser -u bob -- make check",
        "runuser -u bob kill -9 12345",
        "busybox ls -l",
        "chroot /srv/root ls",
        "watch -n 5 'docker ps'",
        "watch -n 1 kill -0 12345",
    ],
)
def test_a_permitted_command_behind_a_new_prefix_passes(command: str) -> None:
    """US-1310: what `busybox`, `su`, `runuser`, `flock`, `watch` and `chroot` run may pass."""
    assert not refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "cd .git && bash -c 'rm index.lock'",
        "cd .git && sh -c 'rm -f *.lock'",
        "cd .git; eval 'rm index.lock'",
        "eval 'cd .git'; rm index.lock",
        "cd .git && trap 'rm index.lock' EXIT",
        "cd .git && flock /tmp/x -c 'rm index.lock'",
        "pushd .git && rm index.lock",
        "pushd .git/refs/heads; rm main.lock",
        "env -C .git rm index.lock",
        "env --chdir=.git rm index.lock",
        "env --ch .git rm index.lock",
        "env -iC .git rm index.lock",
        "sudo -D .git rm index.lock",
        "chroot .git rm index.lock",
        "command cd .git && rm index.lock",
        "builtin cd .git; rm index.lock",
        'cd "$(git rev-parse --git-dir)" && rm index.lock',
        "cd $GIT_DIR && rm index.lock",
        "cd `git rev-parse --git-dir` && rm index.lock",
        "cd .git && cd refs/heads && rm main.lock",
        "cd .git; pushd +1; rm index.lock",
    ],
)
def test_a_cd_into_a_directory_of_git_is_followed(command: str) -> None:
    """US-1310: a `cd` into `.git` is followed into the scripts and past the prefixes.

    Under `bash -c` and `eval`, by `pushd`, `env -C` or `command`; a computed path counts as a
    move into `.git`.
    """
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "cd .git; cd ..; rm foo.lock",
        "cd .git && cd - && rm foo.lock",
        "cd .git; cd /tmp; rm foo.lock",
        "cd .git; cd; rm foo.lock",
        "cd .git; cd ~/scratch; rm foo.lock",
        "cd .git && cd ../tools && rm uv.lock",
        "bash -c 'cd .git' && rm foo.lock",
        "env -C .git git status; rm foo.lock",
        "env -C /tmp rm foo.lock",
        "pushd /tmp && rm foo.lock",
        "cd tools && rm uv.lock",
    ],
)
def test_a_cd_to_a_literal_path_outside_git_resets_the_state(command: str) -> None:
    """US-1310: a `cd` to a literal path outside `.git`, `cd ..` and `cd -` reset the state."""
    assert not refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "env --ch /tmp pkill x",
        "env --chd=/tmp pkill x",
        "env --un HOME pkill x",
        "env --split 'pkill x'",
        "timeout --sig KILL 5 pkill x",
        "timeout --kill 3 5 pkill x",
        "nice --adj 5 pkill x",
        "sudo --us root pkill x",
        "stdbuf --out L pkill x",
        "flock --time 10 /tmp/x pkill x",
        "su --comm 'pkill x'",
        "watch --int 5 pkill x",
        "chroot --user bob / pkill x",
    ],
)
def test_a_long_option_of_a_prefix_takes_its_gnu_abbreviations(command: str) -> None:
    """US-1310: each long option of each prefix admits its unique prefixes, as GNU does."""
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    ["env --ch /tmp make check", "timeout --sig KILL 5 make check", "env --i make check"],
)
def test_a_permitted_command_past_an_abbreviated_option_passes(command: str) -> None:
    """US-1310: an abbreviation takes its argument, and an ambiguous one takes none."""
    assert not refused(command)


@pytest.mark.parametrize(
    ("command", "form"),
    [
        ("docker volume rm $(docker volume ls -q)", "`docker volume rm $(…)`"),
        ("docker rmi -f wf-*", "`docker rmi wf-*`"),
        ("find .git -name '*.lock' -delete", "`find … -delete`"),
        ("mv .git/index.lock /tmp", "`mv .git/index.lock`"),
    ],
)
def test_the_refusal_of_a_new_form_says_what_to_do_instead(
    command: str, form: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """US-1310: the message names the form, and the literal name or the git command again."""
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    assert run(event, monkeypatch) == 2
    said = capsys.readouterr().err
    assert form in said
    assert "`docker rmi` or `docker volume rm` of a literal name" in said
    assert "for a lock of git, the git command run again" in said


def test_docker_compose_v1_takes_unique_prefixes_and_the_go_compose_does_not() -> None:
    """US-1310: `docker-compose` (argparse) abbreviates an option, `docker compose` (Go) not."""
    assert refused("docker-compose --project-n waterfall down")
    assert not refused("docker compose --project-n waterfall down")
    assert not refused("docker-compose --project waterfall make")


def test_a_find_delete_that_names_a_lock_says_why_it_is_refused() -> None:
    """US-1310: `-delete` with a `.lock` in the expression is refused, outside git too, for it."""
    # `package-lock*` does not contain the word `.lock`: it passes.
    form = guard.refusal("find node_modules -name 'package-lock*' -delete")
    assert form is None  # no `.lock` word: `package-lock*` does not name it
    form = guard.refusal("find node_modules -name 'yarn.lock' -delete")
    assert form is not None
    assert "the expression names a .lock" in form
    in_git = guard.refusal("find .git -name 'x' -delete")
    assert in_git is not None
    assert "it is in git" in in_git


def test_popd_is_not_followed_so_a_lock_after_it_stays_refused() -> None:
    """US-1310: `popd` keeps the state of `cd .git`: refused to be on the safe side."""
    assert refused("cd .git; popd; rm foo.lock")


def test_a_cd_up_resets_the_state_even_from_below_git() -> None:
    """US-1310: known limit, `cd ..` resets the state: `cd .git/refs/heads; cd ..` passes."""
    assert not refused("cd .git/refs/heads; cd ..; rm main.lock")


@pytest.mark.parametrize(
    "command",
    [
        "find .git -name '*.lock' | xargs rm",
        "find . -name '*.lock' | xargs -r rm -f",
        "find .git/refs -type f | xargs unlink",
        "ls .git/*.lock | xargs mv -t /tmp",
        "cd .git && find . -name x | xargs rm",
        "rm -rf .git",
        "rm -r .git/",
        "rm -fr ./.git",
        "rm -Rf /home/benjamin/projects/wf-project/.git",
        "rm --recursive --force .git",
        "sudo rm -rf .git",
        "bash -c 'rm -rf .git'",
    ],
)
def test_xargs_rm_of_what_names_git_and_rm_r_of_git_are_refused(command: str) -> None:
    """#2293: `xargs rm` behind a pipe whose source names `.git` or a lock; `rm -r` of `.git`."""
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "find build -name '*.o' | xargs rm",
        "pgrep make | xargs echo",
        "rm -rf build",
        "rm -rf .gitignore",
        "rm -rf frontend/.github",
        "rm .git",
        "rm -rf -- -r .git-old",
        "git status --porcelain | xargs ls",
    ],
)
def test_a_removal_that_neither_reaches_git_nor_follows_its_name_passes(command: str) -> None:
    """#2293: the forms next to those refused."""
    assert not refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "command -v pkill",
        "command -v docker",
        "command -V kill",
        "command -pv killall",
        "command -p -v pkill",
    ],
)
def test_command_looking_a_name_up_runs_nothing(command: str) -> None:
    """#2292: `command -v` asks whether a tool is installed; it is no execution of the tool."""
    assert not refused(command)


@pytest.mark.parametrize(
    "command",
    ["command pkill x", "command -p pkill x", "command -- pkill x", "command -v pkill; pkill x"],
)
def test_command_running_a_name_is_still_judged(command: str) -> None:
    """#2292: without `-v`, `command` runs its operand, which is judged."""
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    [
        "make merge-queue EPIC=EP-21",
        "make EPIC=EP-21 merge-queue",
        "make -C . merge-queue",
        "cd . && make merge-queue",
        "sudo make merge-queue EPIC=EP-21",
        "bash -c 'make merge-queue'",
        "make merge-queue EPIC=$(echo 'EP-21",
    ],
)
def test_the_merge_queue_target_is_refused_to_an_agent(command: str) -> None:
    """#2294: `make merge-queue` creates the rule set with the token of the user: a person's."""
    assert refused(command)


@pytest.mark.parametrize(
    "command",
    ["make merge-queue-check EPIC=EP-21", "make check", "git log --oneline merge-queue"],
)
def test_the_merge_queue_check_and_the_other_targets_pass(command: str) -> None:
    """#2294: `merge-queue-check` only reads, and the other targets of `make` always pass."""
    assert not refused(command)
