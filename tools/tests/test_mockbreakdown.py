# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the skeleton, the attachment and the timelines: commands and refusals (EP-14/L42k).

They try the examples of #586 and of the timelines against the universe they illustrate and
against the contract: the command of the skeleton, where it is offered and its refusal, the
skeleton of the work breakdown by default, the refusals of the attachment by field and the merge
that fails, the command of the timelines and the timeline created — not the Vérif of a
requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockids, mockwitness
from wftools.mockcalendar import Instant, Predecessor, follow
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

SCHEMAS = REPOSITORY / "docs" / "api" / "components" / "schemas"
COMMON = REPOSITORY / "docs" / "api" / "components" / "common.yaml"

SKELETON = "generate_skeleton"
WITHOUT_TASKS = "main_structure_without_tasks"
TIMELINES = "manage_timelines"
NOT_TERMINAL = "project_not_terminal"
TERMINAL = ("completed", "lost", "abandoned")
FORBIDDEN = (409, "STATE_FORBIDS_OPERATION")

CONTROL_STATION, ASSEMBLY, CABINETS = universe(551), universe(711), universe(712)
"""The lot « Poste de commande » of the core, the one order item of the witness it bears, and the
work package of that order item, which no task bears (`mockwitness.ASSEMBLY`, WF-PLA-0170)."""

TOLD: dict[str, tuple[str, str, dict[str, Any]]] = {
    "task_attach_refused": (
        "/order_item_id",
        "WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED",
        {"conflicting_object_id": CONTROL_STATION, "conflicting_object_label": "Poste de commande"},
    ),
    "task_attach_outside_order_item": (
        "/work_package_id",
        "WORK_PACKAGE_OUTSIDE_ORDER_ITEM",
        {
            "order_item_task": {"node_id": CONTROL_STATION, "label": "Poste de commande"},
            "work_package_tasks": [{"node_id": universe(521), "label": "Études"}],
        },
    ),
    "task_attach_exclusive": ("/work_package_id", "WORK_BREAKDOWN_ITEMS_EXCLUSIVE", {}),
    "task_attach_main_structure_only": (
        "/work_package_id",
        "WORK_BREAKDOWN_MAIN_STRUCTURE_ONLY",
        {},
    ),
}
"""What each refusal of the attachment of `updateTaskFacet` tells: the field it names, its motive
and its parameters, none when it has none (`TaskFacetUpdate`, WF-PLA-0170)."""

READERS = {"project_reader": universe(302), "project_pricing_estimator": universe(305)}
"""Who reads the examples of a project that are not read by Camille Martin, the project director:
Dominique Bernard, manager, and Lucas Petit, estimator, as their summaries say."""

SAID = {
    "task_attach_refused": ["« Études »", "« Poste de commande » porte déjà", "son libellé"],
    "task_attach_outside_order_item": ["« Études »", "lot « Armoires »"],
    "task_attach_exclusive": ["« Poste de commande »", "porte déjà le poste", "jamais les deux"],
    "task_attach_main_structure_only": ["devis propre du risque", "structure principale"],
    "task_merge_outside_order_item": [
        "variante déclarée",
        "« Poste de commande »",
        "« Câblage des armoires »",
    ],
}
"""What the summary of each refusal says of the attachment refused."""


def _walk(value: Any) -> list[Entry]:
    """Return every object a value read from JSON holds, itself included."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _walk(item)]
    if not isinstance(value, dict):
        return []
    entry = cast("Entry", value)
    return [entry, *(found for item in entry.values() for found in _walk(item))]


@pytest.fixture(scope="module")
def examples() -> dict[str, Any]:
    """Read every example once, its summary with its value."""
    return {
        path.relative_to(mockwitness.FIXTURES).with_suffix("").as_posix(): json.loads(
            path.read_text(encoding="utf-8")
        )
        for path in sorted(mockwitness.FIXTURES.rglob("*.json"))
    }


def _read(examples: dict[str, Any], keys: set[str]) -> list[tuple[str, Entry]]:
    """Return every object of the examples that holds these keys, with its example."""
    return [
        (name, entry)
        for name, example in examples.items()
        for entry in _walk(example["value"])
        if keys <= entry.keys()
    ]


def _commands(entry: Entry) -> list[tuple[str, bool, list[str]]]:
    return [
        (each["command"], each["is_available"], each["missing_conditions"])
        for each in entry["available_commands"]
    ]


def _enumeration(text: str, schema: str) -> list[str]:
    """Return the values of an enumeration written one a line, in its order."""
    block = text.split(f"\n{schema}:\n", 1)[1].split("\n\n", 1)[0]
    listed = block.split("enum:\n", 1)[1]
    return [line.strip()[2:] for line in listed.splitlines() if line.strip().startswith("- ")]


def _schemas(name: str) -> str:
    return (SCHEMAS / name).read_text(encoding="utf-8")


def _summary(name: str) -> str:
    path = mockwitness.FIXTURES / f"{name}.json"
    return cast("str", json.loads(path.read_text(encoding="utf-8"))["summary"])


def _instant(value: Entry) -> Instant:
    return Instant(date.fromisoformat(value["date"]), Decimal(value["hours"]))


def _span(node: Entry) -> tuple[Instant, Instant]:
    return _instant(node["task"]["start"]), _instant(node["task"]["finish"])


def _permissions(user: str) -> set[str]:
    """Return the permissions a user holds, by the access roles the accounts list give it."""
    [account] = [each for each in fixture("users")["items"] if each["user_id"] == user]
    roles = {each["access_role_id"]: each for each in fixture("access_roles")}
    return {code for role in account["access_role_ids"] for code in roles[role]["permissions"]}


# --- The skeleton, a command of the revision ----------------------------------------------------


def test_the_skeleton_follows_the_entry_of_the_planning_and_lacks_a_main_structure_without_task(
    examples: dict[str, Any],
) -> None:
    revisions = _read(examples, {"revision_id", "status", "available_commands"})
    assert {name for name, _ in revisions} >= {"revision", "revisions", "revision_marking"}
    # The revisions of the witness bear the structure of a thousand tasks, the core first; the
    # revision opened today on the project created bears none (`nodes_empty`).
    assert any(node["kind"] == "task" for node in fixture("volume/nodes_thousand")["items"])
    for name, revision in revisions:
        commands = _commands(revision)
        names = [command for command, _, _ in commands]
        if "edit_planning" not in names:
            # A session without the permission of the planning sees neither (`planning.write`).
            assert SKELETON not in names, name
            continue
        assert names.index(SKELETON) == names.index("edit_planning") + 1, name
        [(_, available, missing)] = [c for c in commands if c[0] == SKELETON]
        [(_, _, entry)] = [c for c in commands if c[0] == "edit_planning"]
        if revision["status"] == "marked":
            # As `merge_structure`: a marked revision lacks its draft alone.
            assert missing == ["revision_draft"], name
        else:
            # The condition proper first, then those of any entry of the current revision; the
            # revision opened today has no task, all the others bear the witness's.
            empty = revision["revision_id"] == fixture("revision_without_tasks")["revision_id"]
            assert missing == [*([] if empty else [WITHOUT_TASKS]), *entry], name
        assert available is (not missing), name


def test_the_skeleton_refused_names_the_first_condition_its_command_lacks() -> None:
    refused, current = fixture("skeleton_structure_not_empty"), fixture("revision")
    assert current["status"] == "draft"
    [missing] = [c[2] for c in _commands(current) if c[0] == SKELETON]
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert (refused["status"], refused["code"]) == FORBIDDEN
    assert refused["params"] == {"missing_condition": missing[0]}
    assert missing[0] == WITHOUT_TASKS
    assert WITHOUT_TASKS in _enumeration(_schemas("projects.yaml"), "CommandCondition")
    assert SKELETON in _enumeration(_schemas("revisions.yaml"), "RevisionCommand")


def test_the_skeleton_is_offered_on_a_main_structure_that_reads_empty_and_there_alone() -> None:
    revision, empty = fixture("revision_without_tasks"), fixture("nodes_empty")
    [structure] = fixture("structures_without_tasks")
    # The revision opened today on the project created today, its main structure, read empty.
    assert revision["project_id"] == fixture("project_created")["project_id"]
    assert (structure["revision_id"], structure["kind"]) == (revision["revision_id"], "main")
    assert empty["items"] == []
    assert empty["totals"]["task_count"] == empty["totals"]["estimate_line_count"] == 0
    assert empty["meta"]["summary_depth"] == 0
    assert (SKELETON, True, []) in _commands(revision)
    # The current revision of the witness reads its tasks: the skeleton is no more offered.
    witness, read = fixture("revision"), fixture("nodes")
    [main] = [each for each in fixture("structures") if each["kind"] == "main"]
    assert main["revision_id"] == witness["revision_id"]
    assert read["items"] != []
    assert read["totals"]["task_count"] > 0
    assert (SKELETON, False, [WITHOUT_TASKS]) in _commands(witness)
    # Its other commands are those of the witness's, but the declaration of a risk, which a main
    # structure without task forbids (EP-14/L42s); the skeleton advances the counter read.
    own = (SKELETON, "declare_risk")
    others = [command for command in _commands(revision) if command[0] not in own]
    assert others == [command for command in _commands(witness) if command[0] not in own]
    assert fixture("skeleton_generated")["structure_lock_version"] == structure["lock_version"] + 1


def test_the_project_created_today_carries_the_revision_opened_without_task() -> None:
    opened, created = fixture("project_revision_opened"), fixture("project_created")
    revision = fixture("revision_without_tasks")
    assert opened["project_id"] == created["project_id"] == revision["project_id"]
    assert opened["label"] == created["label"]
    # The first revision opened leads from created to pricing (WF-CYC-0020).
    assert (created["state"], created["current_revision_id"]) == ("created", None)
    assert opened["current_revision_id"] == revision["revision_id"]
    assert opened["state"] == "pricing"
    assert opened["lock_version"] == created["lock_version"] + 1
    assert revision["audit"]["created_at"] >= created["audit"]["created_at"]
    assert opened["audit"]["updated_at"] >= revision["audit"]["created_at"]
    for key in ("created_at", "created_by"):
        assert opened["audit"][key] == created["audit"][key], key
    # Its commands are those of the project created, but the entry of the risks and the
    # declaration of one, which pass to the revision in progress (WF-RIS-0020; EP-14/L42s), a
    # revision to create, which it has, and the loss, open in pricing (WF-CYC-0060).
    changed: dict[str, tuple[bool, list[str]]] = {
        "create_revision": (False, ["no_current_revision"]),
        "lose": (True, []),
    }
    expected = [
        (command, *changed.get(command, (available, missing)))
        for command, available, missing in _commands(created)
        if command not in ("edit_risks", "declare_risk")
    ]
    assert _commands(opened) == expected
    assert ("edit_risks", True, []) in _commands(revision)
    assert ("declare_risk", False, ["at_least_one_task"]) in _commands(revision)


def test_the_skeleton_of_the_default_breakdown_is_two_summaries_and_their_end_milestones() -> None:
    # « Sur le lotissement par défaut, la génération produit une récapitulative de poste, une
    # récapitulative de lot sans feuille, et leurs deux jalons de fin » (WF-PRJ-0030).
    written = fixture("skeleton_generated")
    [item] = fixture("work_breakdown_default")["order_items"]
    [package] = item["work_packages"]
    assert package["deliverables"] == []
    # « un poste et un lot qui portent le libellé du projet » (WF-PRJ-0020).
    label = fixture("project_created")["label"]
    assert item["label"] == package["label"] == label
    nodes = written["nodes"]
    summary_of_item, summary_of_package, end_of_package, end_of_item = nodes
    facets = [node["task"] for node in nodes]
    # Each summary bears what it stands for, and nothing else (WF-PLA-0170).
    attached = [(f["order_item_id"], f["work_package_id"]) for f in facets[:2]]
    assert attached == [(item["order_item_id"], None), (None, package["work_package_id"])]
    assert [f["work_breakdown_label"] for f in facets[:2]] == [item["label"], package["label"]]
    assert [f["label"] for f in facets[:2]] == [item["label"], package["label"]]
    assert [(f["is_summary"], f["is_milestone"]) for f in facets] == [
        (True, False),
        (True, False),
        (False, True),
        (False, True),
    ]
    # The summary of the package under that of the item; each end milestone under its summary.
    parents = [node["parent_id"] for node in nodes]
    assert parents == [
        None,
        summary_of_item["node_id"],
        summary_of_package["node_id"],
        summary_of_item["node_id"],
    ]
    assert [node["row_number"] for node in nodes] == [1, 2, 3, 4]
    assert [node["level"] for node in nodes] == [1, 2, 3, 2]
    # The end of the item succeeds the end of its packages; the end of a package, its
    # deliverables — none here.
    assert end_of_package["predecessors"] == []
    [link] = end_of_item["predecessors"]
    assert (link["predecessor_node_id"], link["predecessor_row_number"]) == (
        end_of_package["node_id"],
        end_of_package["row_number"],
    )
    assert all(f["duration"]["value"] == "0" for f in facets)
    assert [f["label"] for f in facets[2:]] == [f"Fin de « {label} »"] * 2
    # Dated as the core is: the end of the package at the first hour of the structure, today;
    # the end of the item where a finish-to-start link from it reads its count, the end of the
    # day of work before (WF-PLA-0050); a summary spans its subordinates (WF-PLA-0040).
    calendar = mockwitness.default_calendar()
    origin = _span(end_of_package)[0]
    assert origin == Instant(mockwitness.TODAY.date(), Decimal(0))
    first = follow(calendar, [], Decimal(0), origin)
    assert _span(end_of_package) == first
    assert _span(end_of_item) == follow(calendar, [Predecessor(*first)], Decimal(0), origin)
    for summary, below in ((summary_of_package, [end_of_package]), (summary_of_item, nodes[1::2])):
        spans = [_span(each) for each in below]
        assert _span(summary) == (min(a for a, _ in spans), max(b for _, b in spans))
    # A write of the grid: nothing above to recalculate, the counter of the structure advanced.
    assert (written["ancestors"], written["rescheduled"], written["reinflated"]) == ([], [], [])
    assert written["totals"]["task_count"] == len(nodes)
    assert written["totals"]["estimate_line_count"] == 0
    for node in nodes:
        assert mockids.universe(int(node["node_id"][-3:]) + 100) == node["lineage_id"]


# --- The refusals of the attachment (#586) ------------------------------------------------------


@pytest.mark.parametrize("name", sorted(TOLD))
def test_each_refusal_of_the_attachment_says_its_field_its_motive_and_its_parameters(
    name: str,
) -> None:
    example = fixture(name)
    assert (example["status"], example["code"]) == (422, "VALIDATION_FAILED")
    [field] = example["fields"]
    pointer, code, params = TOLD[name]
    assert (field["pointer"], field["code"], field.get("params", {})) == (pointer, code, params)
    assert code in _enumeration(COMMON.read_text(encoding="utf-8"), "ErrorCode")
    for said in SAID[name]:
        assert said in _summary(name), (name, said)


def test_the_task_the_refusals_name_bears_the_order_item_and_its_package_no_task(
    examples: dict[str, Any],
) -> None:
    # The lot « Poste de commande » bears the one order item, wherever an example reads it: the
    # refusal of a second bearer names it by its node and label; that of the work package
    # alongside, by the exclusivity.
    read = [entry for _, entry in _read(examples, {"node_id", "task"}) if entry["task"]]
    station = [entry["task"] for entry in read if entry["node_id"] == CONTROL_STATION]
    assert station
    assert any("order_item_id" in facet for facet in station)
    for facet in station:
        assert facet["label"] == "Poste de commande"
        if "order_item_id" in facet:
            assert (facet["order_item_id"], facet.get("work_package_id")) == (ASSEMBLY, None)
    assert all(entry["task"].get("work_package_id") != CABINETS for entry in read)


# --- The timelines, a command of the project ----------------------------------------------------


def test_the_timelines_are_listed_to_whoever_may_write_the_planning_unless_the_project_is_closed(
    examples: dict[str, Any],
) -> None:
    projects = _read(examples, {"project_id", "state", "win_probability", "available_commands"})
    assert {"project", "projects", "project_completed", *READERS} <= {name for name, _ in projects}
    assert "Dominique Bernard" in _summary("project_reader")
    assert "chiffreur" in _summary("project_pricing_estimator")
    for name, project in projects:
        commands = _commands(project)
        names = [command for command, _, _ in commands]
        # The command is guarded by the permission of the planning (`planning.write`).
        reader = READERS.get(name, universe(301))
        if "planning.write" not in _permissions(reader):
            assert TIMELINES not in names, name
            continue
        assert names.index(TIMELINES) == names.index("manage_contributors") + 1, name
        missing = [NOT_TERMINAL] if project["state"] in TERMINAL else []
        assert (TIMELINES, not missing, missing) in commands, name
    assert TIMELINES in _enumeration(_schemas("projects.yaml"), "ProjectCommand")


def test_the_merge_that_would_take_the_task_of_a_package_out_fails_naming_both_tasks() -> None:
    # « Une fusion qui déplacerait la tâche d'un lot hors du sous-arbre de la tâche de son poste
    # est refusée en nommant la tâche » (WF-PLA-0170), each by its node and its label.
    task = fixture("task_merge_outside_order_item")
    assert (task["kind"], task["status"], task["result_url"]) == ("structure_merge", "failed", None)
    problem = task["problem"]
    assert (problem["code"], problem["status"]) == ("WORK_PACKAGE_OUTSIDE_ORDER_ITEM", 422)
    station = mockwitness.CONTROL_STATION
    [wiring] = [each for each in station.children if each.number == mockwitness.N.WIRING]
    assert station.order_item == mockwitness.ASSEMBLY
    assert problem["params"] == {
        "order_item_task": {"node_id": mockwitness.node_id(station.number), "label": station.label},
        "work_package_tasks": [
            {"node_id": mockwitness.node_id(wiring.number), "label": wiring.label}
        ],
    }
    for said in SAID["task_merge_outside_order_item"]:
        assert said in _summary("task_merge_outside_order_item"), said


def test_the_timeline_created_is_a_new_one_no_task_is_yet_inscribed_to(
    examples: dict[str, Any],
) -> None:
    created = fixture("timeline_created")
    assert created["timeline_id"] not in {each["timeline_id"] for each in fixture("timelines")}
    family = next(each for each in mockids.IDENTIFIERS if each.what == "chronologies")
    assert family.holds(created["timeline_id"])
    inscribed = {entry["timeline_id"] for _, entry in _read(examples, {"kind", "timeline_id"})}
    assert created["timeline_id"] not in inscribed
    assert re.fullmatch(r".{1,200}", created["label"])


# --- The tasks named by their label, the reports before a merge and an import (EP-14/L42s) -------

PATHS = REPOSITORY / "docs" / "api" / "paths"


def _core() -> dict[str, Entry]:
    """Return the tasks of the core of the witness, by their node."""
    return {node["node_id"]: node for node in fixture("nodes_core")["items"] if node.get("task")}


def _named(node: str) -> Entry:
    """Return how a refusal names a task of the core: its node and its label (WF-IHM-0080)."""
    return {"node_id": node, "label": _core()[node]["task"]["label"]}


WIRING = universe(mockwitness.N.WIRING)
"""« Câblage des armoires », that the variants of #775 and #771 make bear the work package."""

OUTSIDE = {"order_item_task": _named(CONTROL_STATION), "work_package_tasks": [_named(WIRING)]}
"""How the variant names the tasks of the order item and of the work package (WF-PLA-0170)."""


def test_every_refusal_of_a_package_out_of_its_order_item_names_the_tasks_by_their_label() -> None:
    # #775: the refusal of moveNodes, as of updateTaskFacet, createNode and an import, names the
    # task of the order item and those of the packages as the merge that fails does (EP-14/L42k).
    for path in sorted(REPOSITORY.joinpath("docs", "api").rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        assert "order_item_node_id" not in text, path.name
        assert "work_package_node_ids" not in text, path.name
    moved = fixture("nodes_move_outside_order_item")
    [field] = moved["fields"]
    assert (field["pointer"], field["code"]) == ("/node_ids/0", "WORK_PACKAGE_OUTSIDE_ORDER_ITEM")
    assert (
        field["params"] == OUTSIDE == fixture("task_merge_outside_order_item")["problem"]["params"]
    )
    assert "variante déclarée" in _summary("nodes_move_outside_order_item")
    assert "nodes_move_outside_order_item" in (PATHS / "revisions.yaml").read_text(encoding="utf-8")


def test_the_report_before_a_merge_says_what_it_would_do_and_what_refuses_it() -> None:
    # WF-REV-0050 : « Avant application, la fusion présente un compte rendu » — a reading of the
    # path of the merge (#771); its Vérif: the started task the amendment withdraws is named
    # completed, kept, its date nil until the merge is applied.
    revisions = (PATHS / "revisions.yaml").read_text(encoding="utf-8")
    path = revisions.split("structures/{structure_id}/merge:\n", 1)[1].split("\n/", 1)[0]
    assert path.index("operationId: getStructureMergeReport") < path.index("mergeCostStructure")
    report = fixture("structure_merge_report")
    [kept] = [each for each in report["differences"] if each["change"] == "kept"]
    [completed] = report["completed_tasks"]
    desks = universe(mockwitness.N.DESKS)
    assert _core()[desks]["task"]["progress"] == "started"
    assert kept["lineage_id"] == completed["lineage_id"] == _core()[desks]["lineage_id"]
    assert kept["label"] == completed["label"] == _core()[desks]["task"]["label"]
    assert (completed["completed_on"], report["refusals"]) == (None, [])
    refused = fixture("structure_merge_report_refused")
    [refusal] = refused["refusals"]
    assert refusal == {"code": "WORK_PACKAGE_OUTSIDE_ORDER_ITEM", "params": OUTSIDE}
    assert refused["completed_tasks"] == []
    for name in ("structure_merge_report", "structure_merge_report_refused"):
        assert "variante déclarée" in _summary(name), name


def test_the_confirmation_of_a_merge_carries_the_counters_its_report_read() -> None:
    # The user confirms what he read: the counters of the main structure and of the amendment the
    # report read, required by the confirmation, refused by 412 if either changed (WF-REV-0050,
    # WF-IHM-0110; relecture 1).
    counters = ["main_structure_lock_version", "amendment_lock_version"]
    schemas = _schemas("revisions.yaml")
    for schema in ("StructureMerge", "StructureMergeReport"):
        block = schemas.split(f"\n{schema}:\n", 1)[1].split("\n\n", 1)[0]
        required = block.split("properties:", 1)[0]
        assert all(counter in required for counter in counters), schema
    revisions = (PATHS / "revisions.yaml").read_text(encoding="utf-8")
    merge = revisions.split("operationId: mergeCostStructure\n", 1)[1].split("operationId:", 1)[0]
    stale = " ".join(merge.split("      '412':\n", 1)[1].split("content:", 1)[0].split())
    assert "`STALE_LOCK_VERSION`" in stale
    # The counter a 412 names is the one of the object the path names, the amendment, and nothing
    # else, even when the main structure alone changed (#296); the check of both counters and the
    # deposit of the task are one transaction (relecture 2).
    assert "le compteur courant du différentiel, l'objet que le chemin nomme" in stale
    assert "la première qui a changé" not in stale
    assert "le client relit le compte rendu, qui rend l'un et l'autre" in stale
    assert "en une seule transaction" in stale
    # What the report read changes in either tree: 412; what changes outside them makes the task of
    # the merge fail on the motive of the refusal (relecture 2).
    report = revisions.split("operationId: getStructureMergeReport\n", 1)[1]
    read = " ".join(report.split("parameters:", 1)[0].split())
    assert (
        "dans la structure principale ou dans le différentiel fait refuser la confirmation" in read
    )
    assert "par 412" in read
    assert "hors des deux arbres" in read
    assert "fait échouer la tâche de fond sur le motif du refus" in read
    [main] = [each for each in fixture("structures") if each["kind"] == "main"]
    for name in ("structure_merge_report", "structure_merge_report_refused"):
        report = fixture(name)
        assert report["main_structure_lock_version"] == main["lock_version"], name
        assert report["amendment_lock_version"] >= 0, name


def test_a_file_that_would_move_a_package_out_or_pass_the_horizon_is_rejected_whole() -> None:
    # WF-INTF-0040 : « Un fichier qui déplacerait la tâche d'un lot hors du sous-arbre de la tâche
    # de son poste est rejeté au compte rendu, qui nomme les deux tâches, comme un planning qui
    # dépasse l'horizon (WF-PLA-0150) » (#771): not a line, the whole file, nothing applied.
    for path in sorted(mockwitness.FIXTURES.glob("import_*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))["value"].get("report")
        if report is not None and path.stem != "import_planning_rejected":
            assert report["refusals"] == [], path.name
    rejected = fixture("import_planning_rejected")["report"]
    commissioning = universe(mockwitness.N.COMMISSIONING)
    assert rejected["refusals"] == [
        {"code": "WORK_PACKAGE_OUTSIDE_ORDER_ITEM", "params": OUTSIDE},
        {"code": "PROJECT_HORIZON_EXCEEDED", "params": {"task": _named(commissioning)}},
    ]
    assert (
        "WORK_PACKAGE_OUTSIDE_ORDER_ITEM"
        not in _schemas("exchanges.yaml")
        .split("\nImportRejection:\n", 1)[1]
        .split("Une tâche que le fichier", 1)[0]
    )
    assert "PROJECT_HORIZON_EXCEEDED" in _enumeration(
        COMMON.read_text(encoding="utf-8"), "ErrorCode"
    )
    applied = fixture("import_apply_rejected")
    assert (applied["status"], applied["params"]) == (
        409,
        {"missing_condition": "import_file_accepted"},
    )
    conditions = _enumeration(_schemas("projects.yaml"), "CommandCondition")
    assert "import_file_accepted" in conditions


def test_the_work_breakdown_follows_update_and_its_409_names_the_conditions_in_its_order() -> None:
    # #775: the entry of the work breakdown withdraws the attachment of tasks of the current
    # revision. Its command follows update and holds its conditions — no example shows it during
    # a background task, which no project example reads —, and its 409 names each condition the
    # command says missing in an example, then no_background_task_running, in that order (M2).
    enumerated = _enumeration(_schemas("projects.yaml"), "ProjectCommand")
    assert (
        enumerated.index("update_work_breakdown") == enumerated.index("update_win_probability") + 1
    )
    missing: list[str] = []
    for path in sorted(mockwitness.FIXTURES.glob("project*.json")):
        value = cast("Entry", json.loads(path.read_text(encoding="utf-8"))["value"])
        for project in cast("list[Entry]", value.get("items", [value])):
            listed = {
                each["command"]: each
                for each in cast("list[Entry]", project.get("available_commands", []))
            }
            if "update" not in listed:
                continue
            breakdown = listed["update_work_breakdown"]
            assert breakdown["missing_conditions"] == listed["update"]["missing_conditions"], path
            missing += [each for each in breakdown["missing_conditions"] if each not in missing]
    assert missing == ["project_not_terminal"]
    refused = fixture("work_breakdown_background_task")
    assert refused["params"] == {"missing_condition": "no_background_task_running"}
    said = " ".join((PATHS / "projects.yaml").read_text(encoding="utf-8").split())
    said = said.split("operationId: setWorkBreakdown", 1)[1].split("operationId:", 1)[0]
    conflict = said.split("'409':", 1)[1].split("content:", 1)[0]
    told = [conflict.index(f"`{each}`") for each in [*missing, "no_background_task_running"]]
    assert told == sorted(told)
    for counter in (
        "`Node.lock_version`",
        "`CostStructure.lock_version`",
        "`update_work_breakdown`",
    ):
        assert counter in said, counter
