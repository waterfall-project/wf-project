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
BACKGROUND = "no_background_task_running"
"""The condition a background task takes away, which no state of the cycle of life commands."""
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


@pytest.mark.requirement("WF-CYC-0090-A")
def test_the_exit_answers_the_project_or_the_task_and_the_body_bears_the_fate() -> None:
    # Vérif : « La sortie d'un projet qui porte une révision en cours demande de la marquer ou de
    # l'abandonner [...] » : le corps porte ce choix, une variante par sort.
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
    mapping = {"mark": "#/CurrentRevisionMark", "abandon": "#/CurrentRevisionAbandon"}
    assert fate["discriminator"] == {"propertyName": "action", "mapping": mapping}
    assert [each["$ref"] for each in fate["oneOf"]] == list(mapping.values())
    mark, abandon = schemas["CurrentRevisionMark"], schemas["CurrentRevisionAbandon"]
    assert mark["properties"]["action"]["const"] == "mark"
    assert abandon["properties"]["action"]["const"] == "abandon"
    # The name of the version is required with a marking, and bounded as `markRevision` bounds it;
    # an abandon bears neither it nor a description.
    assert mark["required"] == ["action", "version_name"]
    assert abandon["required"] == ["action"]
    assert set(abandon["properties"]) == {"action"}
    revisions = yaml.safe_load((SCHEMAS / "revisions.yaml").read_text("utf-8"))["RevisionMark"]
    for name in ("version_name", "description"):
        assert mark["properties"][name] == revisions["properties"][name]


@pytest.mark.requirement("WF-CYC-0090-A")
@pytest.mark.requirement("WF-IHM-0080-A")
def test_the_task_of_the_exit_is_read_as_the_marking_s_and_runs_again_as_a_task_of_its_own() -> (
    None
):
    # Vérif : « [...] après la sortie, le projet n'a plus de révision en cours, et ses indicateurs
    # se lisent dans sa dernière révision marquée » ; WF-IHM-0080 : « L'échec d'un traitement de
    # fond est signalé avec son motif, et le même traitement peut être relancé. » The follow-up of
    # the front pairs the reads with the task by its identifier: each read of the exit's task bears
    # it, the relaunch a new one (US-0703/L4).
    queued = fixture("task_exit_mark_queued")
    reads = {
        "task_exit_mark_running": "task_running",
        "task_exit_mark_succeeded": "task_succeeded",
        "task_exit_mark_failed": "task_failed",
        "task_exit_mark_relaunched": "task_mark_relaunched",
    }
    instants = ("task_id", "submitted_at", "finished_at")
    for name, marking in reads.items():
        read, model = fixture(name), fixture(marking)
        # The same marking of the 102, the same progress and motive: only the task is its own.
        assert {key: value for key, value in read.items() if key not in instants} == {
            key: value for key, value in model.items() if key not in instants
        }, name
        assert read["task_id"] != model["task_id"], name
    for name in ("task_exit_mark_running", "task_exit_mark_succeeded", "task_exit_mark_failed"):
        read = fixture(name)
        assert (read["task_id"], read["submitted_at"]) == (
            queued["task_id"],
            queued["submitted_at"],
        )
    succeeded, failed = fixture("task_exit_mark_succeeded"), fixture("task_exit_mark_failed")
    assert (succeeded["status"], succeeded["problem"]) == ("succeeded", None)
    assert failed["status"] == "failed"
    assert failed["problem"]["code"] == "HOURLY_RATE_MISSING"
    # Run again after the failure: a task of its own, put in the queue after it.
    relaunched = fixture("task_exit_mark_relaunched")
    others = {queued["task_id"], fixture("task_mark_relaunched")["task_id"]}
    assert relaunched["task_id"] not in others
    assert relaunched["status"] == "queued"
    assert failed["finished_at"] < relaunched["submitted_at"]
    # The exit applied when the task succeeds, under the name its body gives; not when it fails.
    named = f"« {fixture('project_exit_marking')['current_revision']['version_name']} »"
    assert named in _summary("task_exit_mark_succeeded")
    assert CYC_0090 in _summary("task_exit_mark_succeeded")
    assert "la sortie ne s'applique pas" in _summary("task_exit_mark_failed")
    # Declared where the front reads them: the reads of the task, and the exit run again.
    paths = yaml.safe_load((API / "paths" / "system.yaml").read_text("utf-8"))
    task = paths["/tasks/{task_id}"]["get"]["responses"]["200"]["content"]["application/json"]
    declared = {Path(each["$ref"]).stem for each in task["examples"].values()}
    assert set(reads) <= declared
    exit_ = _operation("/projects/{project_id}/exit", "post")["responses"]["202"]
    answered = exit_["content"]["application/json"]["examples"]
    assert {key: Path(each["$ref"]).stem for key, each in answered.items()} == {
        "marking": "task_exit_mark_queued",
        "relaunched": "task_exit_mark_relaunched",
    }


@pytest.mark.requirement("WF-CYC-0090-A")
def test_a_marking_without_a_version_name_or_under_a_name_taken_is_refused() -> None:
    # Vérif : « [...] la sortie n'est appliquée qu'avec ce choix » ; le marquage suit celui de
    # `markRevision` (WF-REV-0020) : un nom exigé, et unique parmi les révisions marquées.
    required = fixture("project_exit_version_name_required")
    assert (required["status"], required["code"]) == (422, "VALIDATION_FAILED")
    assert required["fields"] == [
        {"pointer": "/current_revision/version_name", "code": "VALUE_REQUIRED"}
    ]
    taken = fixture("project_exit_version_name_taken")
    assert (taken["status"], taken["code"]) == (409, "ALREADY_EXISTS")
    [field] = taken["fields"]
    assert (field["pointer"], field["code"]) == (
        "/current_revision/version_name",
        "ALREADY_EXISTS",
    )
    revisions = fixture("revisions")["items"]
    [holder] = [each for each in revisions if each["version_name"] == mockproject.TAKEN_NAME]
    assert holder["status"] == "marked"
    assert field["params"] == {"conflicting_object_id": holder["revision_id"]}
    assert required["correlation_id"] != taken["correlation_id"]
    exit_ = _operation("/projects/{project_id}/exit", "post")["responses"]
    refusals = {"409": "version_name_taken", "422": "version_name_required"}
    for status, key in refusals.items():
        examples = exit_[status]["content"]["application/problem+json"]["examples"]
        assert Path(examples[key]["$ref"]).stem == f"project_exit_{key}"


def _projects() -> list[tuple[str, Entry]]:
    """Every project an example reads or writes, by its file, those of a list each apart."""
    found: list[tuple[str, Entry]] = []
    keys = {"project_id", "state", "available_commands"}
    for path in sorted(FIXTURES.glob("*.json")):
        value: Any = json.loads(path.read_text("utf-8"))["value"]
        paged = isinstance(value, dict) and "meta" in value
        rows = cast("list[Any]", value["items"] if paged else [value])
        found.extend(
            (path.stem, cast("Entry", row))
            for row in rows
            if isinstance(row, dict) and keys <= set(cast("Entry", row))
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
    states: set[str] = set()
    for name, project in _projects():
        commands = _commands(project)
        exits = {
            command: [each for each in missing if each not in (*QUALITIES, BACKGROUND)]
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


@pytest.mark.requirement("WF-CYC-0060-A")
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


@pytest.mark.requirement("WF-PRJ-0010-A")
@pytest.mark.requirement("WF-CRE-0020-A")
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
    assert refused["fields"] == [
        {
            "pointer": "/code",
            "code": "PROJECT_CODE_INVALID",
            "params": {"forbidden_characters": ["/"]},
        }
    ]
    # A code both blank and bearing a slash gets the slash first.
    assert not pattern.search("/  ")
    description = " ".join(_schemas()["ProjectCode"]["description"].split())
    assert "blanc et porteur d'une barre oblique" in description
    assert "`PROJECT_CODE_INVALID`, la barre oblique d'abord" in description


@pytest.mark.requirement("WF-IHM-0090-A")
def test_during_a_marking_the_commands_it_would_make_stale_name_the_task_in_the_background() -> (
    None
):
    # Corps : « Une commande qu'un état du projet, d'une révision ou d'une tâche rend
    # momentanément impossible est présentée indisponible, avec la condition qui manque » ; aucun
    # Vérif ne porte le traitement de fond. #1142, point 5 (US-0660/L2): the entry of the work
    # breakdown unavailable while the marking of `revision_marking` runs, as `setWorkBreakdown`
    # refuses it (`work_breakdown_background_task`) — and the exits, the occurrence and the
    # imports with it; the other commands as the witness lists them.
    witness = _commands(fixture("project"))
    read = fixture("project_background_task_running")
    marking = _commands(read)
    assert marking.keys() == witness.keys()
    suspended = {
        "update_work_breakdown",
        *EXITS,
        "declare_risk_occurrence",
        "import_planning",
        "import_estimate",
        "import_remaining",
    }
    assert suspended == mockproject.SUSPENDED
    for command, missing in marking.items():
        tail = [BACKGROUND] if command in suspended else []
        assert missing == [*witness[command], *tail], command
    assert marking["update_work_breakdown"] == [BACKGROUND]
    listed = cast("list[Entry]", read["available_commands"])
    assert all(each["is_available"] is (not each["missing_conditions"]) for each in listed)
    # The instant of the revision being marked, and of the 409 of the entry it explains; the
    # project itself unchanged, its counter with it.
    assert fixture("revision_marking")["revision_id"] == fixture("project")["current_revision_id"]
    refused = fixture("work_breakdown_background_task")
    assert refused["params"] == {"missing_condition": BACKGROUND}
    attributes = {key: value for key, value in read.items() if key != "available_commands"}
    witnessed = fixture("project")
    assert attributes == {
        key: value for key, value in witnessed.items() if key != "available_commands"
    }
    cited = _operation("/projects/{project_id}", "get")["responses"]["200"]["content"]
    examples = cited["application/json"]["examples"]
    stem = Path(examples["background_task_running"]["$ref"]).stem
    assert stem == "project_background_task_running"
