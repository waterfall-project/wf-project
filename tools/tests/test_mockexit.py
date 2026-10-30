# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the exit of the witness, its exits listed, its code, and its readings by quality.

The review of the contract before the freeze (D-01, D-02, D-06, D-07, J-18, L-25; US-0701/L9):
the examples ``wftools.mockproject`` writes and those written by hand they read, against the
Vérif of WF-CYC-0090, WF-CYC-0060, WF-PRJ-0060 and WF-IHM-0090, and against the contract.
"""

import json
import re
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockproject
from wftools.mockwitness import FIXTURES, fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
SCHEMAS = API / "components" / "schemas"
EXITS = ("complete", "lose", "abandon")
TERMINAL = ("completed", "lost", "abandoned")
QUALITIES = ("is_contributor", "is_project_manager")
CYC_0090 = (
    "après la sortie, le projet n'a plus de révision en cours, et ses indicateurs se lisent dans "
    "sa dernière révision marquée"
)
"""The Vérif of WF-CYC-0090 the examples of the exit say, word for word."""


def _summary(name: str) -> str:
    return cast("str", json.loads((FIXTURES / f"{name}.json").read_text("utf-8"))["summary"])


def _schemas() -> Entry:
    return cast("Entry", yaml.safe_load((SCHEMAS / "projects.yaml").read_text("utf-8")))


def _operation(path: str, method: str) -> Entry:
    paths = yaml.safe_load((API / "paths" / "projects.yaml").read_text("utf-8"))
    return cast("Entry", paths[path][method])


def _commands(project: Entry) -> dict[str, list[str]]:
    return {
        each["command"]: each["missing_conditions"]
        for each in cast("list[Entry]", project["available_commands"])
    }


def _marked(revisions: list[Entry]) -> list[Entry]:
    """Return the marked revisions of a list, the latest marked first."""
    marked = [each for each in revisions if each["status"] == "marked"]
    return sorted(marked, key=lambda each: cast("str", each["marked_at"]), reverse=True)


@pytest.mark.requirement("WF-CYC-0090-A")
def test_after_the_exit_the_project_has_no_revision_in_progress_and_reads_its_last_marked_one() -> (
    None
):
    # Vérif : « La sortie d'un projet qui porte une révision en cours demande de la marquer ou de
    # l'abandonner ; après la sortie, le projet n'a plus de révision en cours, et ses indicateurs
    # se lisent dans sa dernière révision marquée (WF-IND-0010). »
    witness = fixture("project")
    current = witness["current_revision_id"]
    revisions = fixture("revisions")["items"]
    assert [each["status"] for each in revisions if each["revision_id"] == current] == ["draft"]
    # Abandoned: answered 200 with the project, which has no revision in progress, its last
    # marked revision the reference, « Référence », where its indicators are read.
    abandoning = fixture("project_exit_abandoning")
    assert abandoning["current_revision"] == {"action": "abandon"}
    completed = fixture("project_completed")
    assert completed["state"] == abandoning["to_state"] in TERMINAL
    assert completed["current_revision_id"] is None
    assert completed["reference_revision_id"] == witness["reference_revision_id"]
    [last, *_] = _marked([each for each in revisions if each["revision_id"] != current])
    assert last["revision_id"] == completed["reference_revision_id"]
    assert f"« {last['version_name']} »" in _summary("project_completed")
    # Marked: answered 202 with the task of the marking, under a name no marked revision bears,
    # the last marked revision once it succeeds (WF-REV-0020).
    marking = fixture("project_exit_marking")
    fate = marking["current_revision"]
    assert fate["action"] == "mark"
    assert fate["version_name"] not in {each["version_name"] for each in _marked(revisions)}
    task = fixture("task_exit_mark_queued")
    assert (task["kind"], task["status"], task["finished_at"]) == ("revision_mark", "queued", None)
    assert task["task_id"] != fixture("task_mark_queued")["task_id"]
    assert f"« {fate['version_name']} »" in _summary("project_exit_marking")
    for name in ("project_completed", "project_exit_abandoning", "project_exit_marking"):
        assert CYC_0090 in _summary(name), name
    # The fate refused when missing, nothing written.
    refused = fixture("project_exit_revision_required")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [{"pointer": "/current_revision", "code": "VALUE_REQUIRED"}]


def test_the_exit_answers_the_project_or_the_task_and_the_body_bears_the_fate() -> None:
    exit_ = _operation("/projects/{project_id}/exit", "post")
    responses = exit_["responses"]
    assert responses["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/Project")
    assert responses["202"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BackgroundTaskRef"
    )
    bodies = exit_["requestBody"]["content"]["application/json"]["examples"]
    assert {Path(each["$ref"]).stem for each in bodies.values()} == {
        "project_exit_abandoning",
        "project_exit_marking",
    }
    schemas = _schemas()
    fate = schemas["CurrentRevisionFate"]
    assert schemas["CurrentRevisionFateAction"]["enum"] == ["mark", "abandon"]
    assert fate["then"]["required"] == ["action", "version_name"]
    # The name of the version is bounded as `markRevision` bounds it.
    revisions = yaml.safe_load((SCHEMAS / "revisions.yaml").read_text("utf-8"))
    assert (
        fate["properties"]["version_name"]
        == revisions["RevisionMark"]["properties"]["version_name"]
    )


def _projects() -> list[tuple[str, Entry]]:
    """Every project an example reads or writes, by its file, those of a list each apart."""
    found: list[tuple[str, Entry]] = []
    keys = {"project_id", "state", "available_commands"}
    for path in sorted(FIXTURES.glob("*.json")):
        value = json.loads(path.read_text("utf-8")).get("value")
        rows = value.get("items") if isinstance(value, dict) and "meta" in value else [value]
        listed = rows if isinstance(rows, list) else []
        found.extend(
            (path.stem, row) for row in listed if isinstance(row, dict) and keys <= set(row)
        )
    return found


def _exits(state: str) -> dict[str, list[str]]:
    """Return the exits a project lists in a state, each with its condition of state missing."""
    if state in TERMINAL:
        return {}
    listed = {"complete": [] if state == "in_progress" else ["project_in_progress"]}
    if state in ("created", "pricing"):
        listed["lose"] = ["project_in_pricing"] if state == "created" else []
    listed["abandon"] = []
    return listed


@pytest.mark.requirement("WF-CYC-0060-A")
def test_an_exit_that_will_never_become_possible_is_not_listed() -> None:
    # Vérif : « Pour chaque état non terminal, le menu des sorties ne permet que les sorties
    # permises depuis cet état. Une sortie qui le deviendra dans un état ultérieur — Terminer
    # depuis Chiffrage — y est présentée indisponible, avec sa condition (WF-IHM-0090) ; une
    # sortie qui ne le deviendra jamais — Déclarer perdu depuis En cours — n'y figure pas. »
    states = set()
    for name, project in _projects():
        commands = _commands(project)
        exits = {
            command: [each for each in missing if each not in QUALITIES]
            for command, missing in commands.items()
            if command in EXITS
        }
        if not exits and project["state"] not in TERMINAL:
            continue  # whom no permission of an exit lets see one (`project_reader`)
        assert exits == _exits(project["state"]), name
        states.add(project["state"])
    assert {"created", "pricing", "in_progress", "completed"} <= states
    in_progress = _commands(fixture("project"))
    assert "lose" not in in_progress
    assert in_progress["complete"] == in_progress["abandon"] == []


def test_the_presence_of_the_exits_is_written_where_the_contract_describes_the_commands() -> None:
    command = " ".join(_schemas()["ProjectCommand"]["description"].split())
    assert "Déclarer perdu depuis En cours — n'y figure pas" in command
    assert "Un projet terminal n'en liste aucune" in command


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_without_an_active_project_manager_a_non_contributor_may_enter_one() -> None:
    # Corps : « Lorsque le compte du dernier chef de projet est désactivé (WF-ADM-0060), un
    # utilisateur portant la permission de modifier FBS-4.2 et celle de consulter tous les projets
    # peut y inscrire un chef de projet ; c'est la seule saisie ouverte à un non-contributeur. »
    read = fixture("contributors_without_active_manager")
    rows = cast("list[Entry]", read["items"])
    managers = [each for each in rows if each["kind"] == "project_manager"]
    assert managers
    assert not any(each["is_active"] for each in managers)
    assert read["lock_version"] == fixture("contributors")["lock_version"]
    roles = {each["label"]: each for each in fixture("access_roles")}
    held = set(roles["Direction de projet"]["permissions"])
    assert {"project_settings.write", "all_projects_read"} <= held
    assert mockproject.RESCUER not in {each["user_id"] for each in rows}
    written = fixture("contributors_set_by_rescuer")
    assert written["lock_version"] == read["lock_version"] + 1
    entered = [
        each for each in written["items"] if each["kind"] == "project_manager" and each["is_active"]
    ]
    assert [each["user_id"] for each in entered] == [mockproject.PARTICIPANT]
    unchanged = [each for each in written["items"] if each["user_id"] != mockproject.PARTICIPANT]
    assert sorted(unchanged, key=str) == sorted(
        [each for each in rows if each["user_id"] != mockproject.PARTICIPANT], key=str
    )
    rescue = _commands(fixture("project_rescue"))
    assert rescue.pop("manage_contributors") == []
    assert rescue
    assert all(missing[0] == "is_contributor" for missing in rescue.values())


@pytest.mark.requirement("WF-IHM-0090-A")
def test_a_command_the_quality_does_not_allow_names_that_quality() -> None:
    # Corps : « Une commande que la qualité de l'utilisateur sur le projet ne permet pas —
    # non-contributeur, ou participant pour une action réservée aux chefs de projet (WF-PRJ-0060)
    # — est présentée indisponible, en nommant cette qualité. »
    witness = _commands(fixture("project"))
    participant = _commands(fixture("project_participant"))
    assert participant.keys() == witness.keys()
    for command, missing in participant.items():
        if command in mockproject.RESERVED:
            assert missing == ["is_project_manager", *witness[command]], command
        else:
            assert missing == witness[command], command
    people = fixture("contributors")["items"]
    [row] = [each for each in people if each["user_id"] == mockproject.PARTICIPANT]
    assert row["kind"] == "contributor"
    rescue = _commands(fixture("project_rescue"))
    for command, missing in rescue.items():
        if command == "manage_contributors":
            continue
        quality = ["is_contributor"] + (
            ["is_project_manager"] if command in mockproject.RESERVED else []
        )
        assert missing == [*quality, *witness[command]], command


def test_the_project_code_is_never_blank_and_bears_no_slash() -> None:
    code = _schemas()["ProjectCode"]
    assert (code["minLength"], code["maxLength"]) == (1, 50)
    pattern = re.compile(code["pattern"])
    for accepted in ("PRJ-001", "PRJ.2026.01", "A", "PRJ 001"):
        assert pattern.search(accepted), accepted
    for refused in ("   ", "PRJ/001", "/", "PRJ-001/SP-CMD", mockproject.INVALID_CODE):
        assert not pattern.search(refused), refused
    for name, project in _projects():
        assert project["code"] is None or pattern.search(project["code"]), name
    for schema in ("Project", "ProjectSummary", "ProjectCreate", "ProjectUpdate"):
        assert _schemas()[schema]["properties"]["code"]["anyOf"][0] == {"$ref": "#/ProjectCode"}
    refused = fixture("project_code_invalid")
    assert refused["fields"] == [{"pointer": "/code", "code": "PROJECT_CODE_INVALID"}]
