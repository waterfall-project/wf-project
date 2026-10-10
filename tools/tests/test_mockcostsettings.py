# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the writes of the cost settings: their commands and their refusals (EP-02/L42g, #562).

They try the examples of the natures, the categories and the hourly rates against the universe they
illustrate and against the contract, not the Vérif of a requirement: none cites one (WF-QUA-0010,
« un test qui ne couvre aucune exigence »).
"""

import json
import re
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"

CONTRACT = sorted(
    [API / "openapi.yaml", *(API / "paths").glob("*.yaml"), *(API / "components").rglob("*.yaml")]
)
"""The files of the contract written by hand: never a bundle `make build-openapi` writes beside."""

CHANGE_KIND = "change_kind"
UNUSED, UNRATED, WITHOUT_ROLE = "cost_type_unused", "cost_type_unrated", "cost_type_without_role"
CHANGE_COST_TYPE = "change_cost_type"
CATEGORY_UNUSED, CATEGORY_UNRATED = "cost_category_unused", "cost_category_unrated"
CATEGORY_WITHOUT_ROLE = "cost_category_without_role"
WITHDRAWN = ("cost_type_not_last_provision", "cost_category_not_last_provision")
"""The conditions of the rule of #578, withdrawn with it (EP-14/L42p, #579)."""

TEXTS = {"/code", "/label", "/accounting_code"}
"""The fields of a nature or a category that hold a text the schema bounds."""

REFUSALS = {
    **{pointer: frozenset({"VALUE_REQUIRED", "VALUE_TOO_LONG"}) for pointer in TEXTS},
    "/cost_type_id": frozenset(
        {"VALUE_REQUIRED", "UNKNOWN_COST_TYPE", "INACTIVE_REFERENCE_OBJECT"}
    ),
}
"""The motives by field of a write of the cost settings, by pointer (`createCostCategory`)."""

TOLD: dict[str, tuple[int, str, list[tuple[str, str]], dict[str, str]]] = {
    "cost_type_code_taken": (409, "ALREADY_EXISTS", [("/code", "ALREADY_EXISTS")], {}),
    "cost_type_creation_refused": (
        422,
        "VALIDATION_FAILED",
        [("/code", "VALUE_TOO_LONG"), ("/label", "VALUE_REQUIRED")],
        {},
    ),
    "cost_type_kind_refused": (409, "STATE_FORBIDS_OPERATION", [], {"missing_condition": UNUSED}),
    "cost_type_update_refused": (422, "VALIDATION_FAILED", [("/label", "VALUE_REQUIRED")], {}),
    "cost_category_codes_taken": (
        409,
        "ALREADY_EXISTS",
        [("/code", "ALREADY_EXISTS"), ("/accounting_code", "ALREADY_EXISTS")],
        {},
    ),
    "cost_category_creation_refused": (
        422,
        "VALIDATION_FAILED",
        [("/cost_type_id", "UNKNOWN_COST_TYPE"), ("/accounting_code", "VALUE_REQUIRED")],
        {},
    ),
    "cost_category_without_type_refused": (
        422,
        "VALIDATION_FAILED",
        [("/cost_type_id", "VALUE_REQUIRED")],
        {},
    ),
    "cost_category_accounting_code_taken": (
        409,
        "ALREADY_EXISTS",
        [("/accounting_code", "ALREADY_EXISTS")],
        {},
    ),
    "cost_category_update_refused": (422, "VALIDATION_FAILED", [("/label", "VALUE_TOO_LONG")], {}),
    "hourly_rate_already_entered": (409, "ALREADY_EXISTS", [], {}),
    "hourly_rate_amount_refused": (
        422,
        "VALIDATION_FAILED",
        [("/amount", "VALUE_OUT_OF_RANGE")],
        {},
    ),
    "hourly_rate_non_labour_refused": (422, "LABOUR_CATEGORY_REQUIRED", [], {}),
}
"""What each refusal of the cost settings tells, as its summary says it: its status and code, the
fields it names with their motive, in order, and its parameters."""

SAID = {
    "cost_type_code_taken": ["sous le code DEB"],
    "cost_type_creation_refused": ["sans libellé", "trente-six caractères"],
    "cost_type_kind_refused": ["passés en main-d'œuvre"],
    "cost_type_update_refused": ["libellé vide"],
    "cost_category_codes_taken": ["code ACH-002", "code comptable 604001"],
    "cost_category_creation_refused": [
        "une nature que le référentiel n'a pas",
        "sans code comptable",
    ],
    "cost_category_without_type_refused": ["sans nature"],
    "cost_category_accounting_code_taken": ["code comptable 604002"],
    "cost_category_update_refused": ["deux cent un caractères"],
    "hourly_rate_already_entered": ["sans version", "86,98"],
    "hourly_rate_amount_refused": ["corrigé à 0,00"],
    "hourly_rate_non_labour_refused": ["une catégorie des débours"],
}
"""What the summary of each refusal says of the value sent, by the fields and motives it tells."""

RELIT = ("updateCostCategory", "setHourlyRate", "createResourceRole", "updateResourceRole")
"""The writes of the reference that change the commands of other objects than the one written,
which the answer does not bear (#577): each says the client reads the lists anew — a role attached
to a category freezes its move and the kind of its nature (EP-14/L42r). Those #578 named change none
since its rule was withdrawn (EP-14/L42p)."""

TOO_LONG = {
    "cost_type_creation_refused": ("CostTypeWrite", "code", 36, "trente-six"),
    "cost_category_update_refused": ("CostCategoryWrite", "label", 201, "deux cent un"),
}
"""The texts a refusal says too long: the schema and field, the length its summary tells."""

SMALLEST_RATE = Decimal("0.01")
"""The smallest positive amount a `Money` writes, two decimals."""


def _every_example() -> dict[str, Any]:
    return {
        path.relative_to(mockwitness.FIXTURES).with_suffix("").as_posix(): json.loads(
            path.read_text(encoding="utf-8")
        )
        for path in sorted(mockwitness.FIXTURES.rglob("*.json"))
    }


@pytest.fixture(scope="module")
def examples() -> dict[str, Any]:
    """Read every example once, its summary with its value."""
    return _every_example()


def _walk(value: Any) -> list[Entry]:
    """Return every object a value read from JSON holds, itself included."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _walk(item)]
    if not isinstance(value, dict):
        return []
    entry = cast("Entry", value)
    return [entry, *(found for item in entry.values() for found in _walk(item))]


def _categories() -> dict[str, Entry]:
    return {
        category["cost_category_id"]: category
        for category in fixture("volume/cost_categories")["items"]
    }


def _employed(examples: dict[str, Any]) -> set[str]:
    """Return the natures whose categories a line of an example bears."""
    categories = _categories()
    return {
        categories[entry["estimate_line"]["cost_category_id"]]["cost_type_id"]
        for example in examples.values()
        for entry in _walk(example["value"])
        if isinstance(entry.get("estimate_line"), dict)
    }


def _attached() -> set[str]:
    """Return the categories a resource role is attached to, deactivated roles counted."""
    return {role["cost_category_id"] for role in fixture("resource_roles")["items"]}


def _natures_of(categories: set[str]) -> set[str]:
    """Return the natures some of the categories given belong to."""
    return {_categories()[identifier]["cost_type_id"] for identifier in categories}


def _nature_commands(nature: Entry, employed: set[str], examples: dict[str, Any]) -> list[Entry]:
    """Return the commands a nature bears: its state's, always available, then its kind's.

    The kind misses, in that order, a category employed, one that bears hourly rates and one a role
    is attached to (WF-REF-0030).
    """
    held = (
        (UNUSED, employed),
        (UNRATED, _natures_of(_rated(examples))),
        (WITHOUT_ROLE, _natures_of(_attached())),
    )
    frozen = [condition for condition, natures in held if nature["cost_type_id"] in natures]
    return [
        {
            "command": "deactivate" if nature["is_active"] else "reactivate",
            "is_available": True,
            "missing_conditions": [],
        },
        {"command": CHANGE_KIND, "is_available": not frozen, "missing_conditions": frozen},
    ]


# --- The kind of a nature: frozen once one of its categories is employed ------------------------


def test_the_kind_of_a_nature_is_frozen_by_a_category_employed_rated_or_attached_to_a_role(
    examples: dict[str, Any],
) -> None:
    employed = _employed(examples)
    natures = fixture("cost_types")["items"]
    # The estimate of the witness is broken down by the three natures: each has its kind frozen.
    assert employed == {nature["cost_type_id"] for nature in natures}
    written = [fixture(name) for name in ("cost_type_updated", "cost_type_deactivated")]
    listed = [*natures, *fixture("cost_types_with_inactive")["items"], *written]
    for nature in listed:
        expected = _nature_commands(nature, employed, examples)
        assert nature["available_commands"] == expected, nature["label"]
    # The labour (461) alone misses the three: its categories bear rates, two of them roles.
    [labour] = [n for n in natures if n["kind"] == "labor"]
    assert labour["cost_type_id"] == universe(461)
    assert labour["available_commands"][1]["missing_conditions"] == [UNUSED, UNRATED, WITHOUT_ROLE]
    # The nature created today has no category yet: its kind may still change.
    created = fixture("cost_type_created")
    assert created["cost_type_id"] not in {c["cost_type_id"] for c in _categories().values()}
    assert created["available_commands"] == _nature_commands(created, employed, examples)
    assert created["available_commands"][1]["is_available"] is True


def _kind_of_object(entry: Entry) -> str:
    """Name what an object of the reference is: a category, a nature, or another."""
    if "cost_category_id" in entry and "cost_type_label" in entry:
        return "category"
    if "cost_type_id" in entry and "kind" in entry:
        return "nature"
    return "other"


def test_a_change_of_kind_is_offered_by_a_nature_and_a_change_of_nature_by_a_category(
    examples: dict[str, Any],
) -> None:
    owners = {CHANGE_KIND: "nature", CHANGE_COST_TYPE: "category"}
    offered: dict[str, int] = dict.fromkeys(owners, 0)
    for name, example in examples.items():
        for entry in _walk(example["value"]):
            commands = entry.get("available_commands")
            if not isinstance(commands, list):
                continue
            for each in cast("list[Entry]", commands):
                if each["command"] in owners:
                    assert _kind_of_object(entry) == owners[each["command"]], name
                    offered[each["command"]] += 1
    assert all(offered.values())


def test_the_refused_change_of_kind_names_the_condition_its_command_misses(
    examples: dict[str, Any],
) -> None:
    example = examples["cost_type_kind_refused"]
    refused, summary = example["value"], example["summary"].lower()
    natures = [*fixture("cost_types")["items"], fixture("cost_type_created")]
    # The nature the summary names first, by its label.
    told = [(summary.find(n["label"].lower()), n) for n in natures if n["label"].lower() in summary]
    [_, debours] = min(told, key=lambda pair: pair[0])
    assert debours["cost_type_id"] == universe(462)
    [_, change] = debours["available_commands"]
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert [refused["params"]["missing_condition"]] == change["missing_conditions"]
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert list(refused["params"]) == ["missing_condition"]


# --- The nature of a category: of the same kind once employed, or once it bears rates (#577) ----


def _rated(examples: dict[str, Any]) -> set[str]:
    """Return the categories an hourly rate of an example belongs to."""
    return {
        entry["cost_category_id"]
        for example in examples.values()
        for entry in _walk(example["value"])
        if {"cost_category_id", "year", "amount"} <= entry.keys()
    }


def _lined(examples: dict[str, Any]) -> set[str]:
    """Return the categories a line of an example bears."""
    return {
        entry["estimate_line"]["cost_category_id"]
        for example in examples.values()
        for entry in _walk(example["value"])
        if isinstance(entry.get("estimate_line"), dict)
    }


def test_a_category_changes_kind_only_unemployed_without_rates_and_without_role(
    examples: dict[str, Any],
) -> None:
    lined, rated, attached = _lined(examples), _rated(examples), _attached()
    listed = list(_categories().values())
    written = [
        fixture(name)
        for name in ("cost_category_created", "cost_category_updated", "cost_category_deactivated")
    ]
    seen: set[tuple[str, ...]] = set()
    for category in [*listed, *written]:
        identifier = category["cost_category_id"]
        missing = [
            condition
            for condition, held in (
                (CATEGORY_UNUSED, identifier in lined),
                (CATEGORY_UNRATED, identifier in rated),
                (CATEGORY_WITHOUT_ROLE, identifier in attached),
            )
            if held
        ]
        seen.add(tuple(missing))
        assert category["available_commands"] == [
            {
                "command": "deactivate" if category["is_active"] else "reactivate",
                "is_available": True,
                "missing_conditions": [],
            },
            {
                "command": CHANGE_COST_TYPE,
                "is_available": not missing,
                "missing_conditions": missing,
            },
        ], category["code"]
    # Every case of the universe is told: free, employed, bearing rates, and the three — the
    # electrical engineering (402) and the commissioning (405), employed and rated, that the roles
    # are attached to.
    assert seen == {
        (),
        (CATEGORY_UNUSED,),
        (CATEGORY_UNRATED,),
        (CATEGORY_UNUSED, CATEGORY_UNRATED, CATEGORY_WITHOUT_ROLE),
    }
    assert attached == {universe(402), universe(405)}


# --- The last of provision for risks goes as any other: #578 withdrawn (EP-14/L42p) --------------


def test_the_one_nature_of_provision_and_its_one_category_deactivate_as_any_other(
    examples: dict[str, Any],
) -> None:
    # The witness has one nature of provision for risks, PRV (463), and one category of it, PRV-001
    # (404): their deactivation is available, the creation of a project and the declaration of a
    # risk naming what they then miss (WF-CYC-0120, WF-RIS-0010; #579).
    [nature] = [n for n in fixture("cost_types")["items"] if n["kind"] == "provision"]
    assert nature["cost_type_id"] == universe(463)
    assert nature["available_commands"][0] == {
        "command": "deactivate",
        "is_available": True,
        "missing_conditions": [],
    }
    [category] = [c for c in _categories().values() if c["cost_type_id"] == universe(463)]
    assert category["cost_category_id"] == universe(404)
    assert category["available_commands"][0]["is_available"] is True
    assert "cost_type_last_provision_refused" not in examples
    assert "cost_category_last_provision_refused" not in examples


def test_no_file_of_the_contract_names_the_conditions_of_the_withdrawn_rule() -> None:
    for path in CONTRACT:
        text = path.read_text(encoding="utf-8")
        for condition in WITHDRAWN:
            assert condition not in text, (path.name, condition)
    for name in ("setCostTypeActivation", "setCostCategoryActivation"):
        text = (API / "paths" / "reference.yaml").read_text(encoding="utf-8")
        block = text.split(f"operationId: {name}\n", 1)[1].split("operationId:", 1)[0]
        assert "\n      '409':" not in block, name


@pytest.mark.parametrize(
    ("operation", "conditions"),
    [
        ("updateCostType", (UNUSED, UNRATED, WITHOUT_ROLE)),
        ("updateCostCategory", (CATEGORY_UNUSED, CATEGORY_UNRATED, CATEGORY_WITHOUT_ROLE)),
    ],
)
def test_a_refused_change_of_kind_names_the_first_condition_missing_in_the_order_of_the_catalogue(
    operation: str, conditions: tuple[str, ...]
) -> None:
    # The order of WF-REF-0030 and WF-REF-0040 — employed, bearing rates, attached to a role —,
    # which puts first what no action lifts: the lines of a marked revision stay, a rate is not
    # removed, a role changes its category (EP-14/L42r).
    said = conflict_said((API / "paths" / "reference.yaml").read_text(encoding="utf-8"), operation)
    places = [said.find(f"`{condition}`") for condition in conditions]
    assert -1 not in places, operation
    assert places == sorted(places), operation
    schema = (API / "components" / "schemas" / "projects.yaml").read_text(encoding="utf-8")
    block = schema.split("\nCommandCondition:\n", 1)[1].split("\n\n", 1)[0]
    listed = re.findall(r"^    - (\w+)$", block, flags=re.MULTILINE)
    assert [listed.index(condition) for condition in conditions] == sorted(
        listed.index(condition) for condition in conditions
    )


@pytest.mark.parametrize(
    ("operation", "condition"),
    [("updateCostType", WITHOUT_ROLE), ("updateCostCategory", CATEGORY_WITHOUT_ROLE)],
)
def test_a_change_of_kind_refused_for_its_roles_names_them(operation: str, condition: str) -> None:
    # WF-IHM-0090: a condition that an action lifts says what to do — move the roles named, all of
    # them, active or deactivated, to another category of labour —, each by what the screen of the
    # cost settings, which does not read the deactivated roles, can show (EP-14/L42r, revue 2).
    said = " ".join(
        conflict_said(
            (API / "paths" / "reference.yaml").read_text(encoding="utf-8"), operation
        ).split()
    )
    assert f"`{condition}` ; nommant celle-ci, `params.resource_roles` les rôles" in said
    assert "chacun par son identifiant, son code et son libellé" in said
    assert "resource_role_ids" not in said
    common = (API / "components" / "common.yaml").read_text(encoding="utf-8")
    problem = " ".join(common.split("\nProblem:\n", 1)[1].split("\n\n", 1)[0].split())
    assert (
        "`resource_roles` quand `missing_condition` nomme `cost_type_without_role` ou"
        " `cost_category_without_role`"
    ) in problem
    assert (
        "tous les rôles en cause, actifs ou désactivés, chacun par son identifiant, son code et son"
        " libellé (`resource_role_id`, `code`, `label`)"
    ) in problem
    assert (
        "à rattacher d'abord à une catégorie de main-d'œuvre hors de la catégorie, ou de la"
        " nature, refusée"
    ) in problem


def test_the_category_refused_for_its_role_names_it_by_its_code_and_label(
    examples: dict[str, Any],
) -> None:
    # A declared counterfactual variant, its two departures said: no category of labour of the
    # witness is without rates, and the automation engineer (453), deactivated, is attached to the
    # electrical engineering, employed and rated (EP-14/L42r, revues 2 and 3).
    example = examples["cost_category_role_kind_refused"]
    refused = example["value"]
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert list(refused["params"]) == ["missing_condition", "resource_roles"]
    assert refused["params"]["missing_condition"] == CATEGORY_WITHOUT_ROLE
    roles = {role["resource_role_id"]: role for role in fixture("resource_roles")["items"]}
    named = refused["params"]["resource_roles"]
    assert named
    for each in named:
        assert set(each) == {"resource_role_id", "code", "label"}
        role = roles[each["resource_role_id"]]
        assert (each["code"], each["label"]) == (role["code"], role["label"])
        assert role["is_active"] is False
        assert role["label"].lower() in example["summary"]
        assert role["cost_category_id"] == universe(402)
    assert universe(402) in _lined(examples)
    assert universe(402) in _rated(examples)
    labour = {
        c["cost_category_id"] for c in _categories().values() if c["cost_type_kind"] == "labor"
    }
    assert labour <= _rated(examples)
    assert example["summary"].endswith(
        "Une variante contrefactuelle : aucune catégorie de main-d'œuvre du témoin n'est sans"
        " taux, et l'automaticien y est rattaché à l'ingénierie électrique, employée et qui porte"
        " des taux (WF-REF-0040, WF-IHM-0090)."
    )
    # Cited last under the 409, the first — the one the fake back serves — unchanged.
    said = conflict_said(
        (API / "paths" / "reference.yaml").read_text(encoding="utf-8"), "updateCostCategory"
    )
    cited = re.findall(r"fixtures/api/(\w+)\.json", said)
    assert cited[0] == "cost_category_accounting_code_taken"
    assert cited[-1] == "cost_category_role_kind_refused"


@pytest.mark.parametrize(
    ("name", "category"),
    [("cost_category_kind_refused", universe(402)), ("cost_category_rated_kind_refused", None)],
)
def test_the_refused_change_of_nature_names_the_first_condition_its_command_misses(
    examples: dict[str, Any], name: str, category: str | None
) -> None:
    example = examples[name]
    refused = example["value"]
    by_code = {each["code"]: each for each in _categories().values()}
    [code] = [code for code in by_code if f"{code}," in example["summary"]]
    named = by_code[code]
    if category is not None:
        assert named["cost_category_id"] == category
    [_, move] = named["available_commands"]
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert refused["params"] == {"missing_condition": move["missing_conditions"][0]}


def test_the_category_refused_for_its_rates_alone_is_unemployed_and_of_labour(
    examples: dict[str, Any],
) -> None:
    refused = fixture("cost_category_rated_kind_refused")
    assert refused["params"] == {"missing_condition": CATEGORY_UNRATED}
    [mechanical] = [c for c in _categories().values() if c["code"] == "MO-003"]
    assert mechanical["cost_category_id"] not in _lined(examples)
    assert mechanical["cost_category_id"] in _rated(examples)
    kinds = {nature["cost_type_id"]: nature["kind"] for nature in fixture("cost_types")["items"]}
    # A category bears rates only in labour: leaving it is what the rates forbid (WF-REF-0050).
    for identifier in _rated(examples):
        assert kinds[_categories()[identifier]["cost_type_id"]] == "labor"


# --- The codes: unique, and the refusal names which field bears a value taken ----------------


@pytest.mark.parametrize(
    ("name", "listed"),
    [
        ("cost_type_code_taken", "cost_types"),
        ("cost_category_codes_taken", "volume/cost_categories"),
        ("cost_category_accounting_code_taken", "volume/cost_categories"),
        ("subproject_code_taken", "subprojects"),
        ("org_node_code_taken", "org_nodes_with_inactive"),
        ("calendar_label_taken", "calendars_with_inactive"),
        ("resource_role_code_taken", "resource_roles"),
    ],
)
def test_a_code_taken_names_its_field_and_the_object_that_bears_it(
    examples: dict[str, Any], name: str, listed: str
) -> None:
    example = examples[name]
    refused, summary = example["value"], example["summary"]
    read = fixture(listed)
    entries = cast("list[Entry]", read["items"] if isinstance(read, dict) else read)
    objects = {next(v for k, v in entry.items() if k.endswith("_id")): entry for entry in entries}
    assert (refused["status"], refused["code"]) == (409, "ALREADY_EXISTS")
    assert "params" not in refused
    pointers = [field["pointer"] for field in refused["fields"]]
    assert pointers, name
    assert len(set(pointers)) == len(pointers)
    for field in refused["fields"]:
        assert field["code"] == "ALREADY_EXISTS", name
        assert field["pointer"] in {"/code", "/accounting_code", "/label"}, name
        assert list(field["params"])[:1] == ["conflicting_object_id"], name
        bearer = objects[field["params"]["conflicting_object_id"]]
        # The summary says the value sent: the one the object named bears in that field.
        assert bearer[field["pointer"].removeprefix("/")] in summary, name


def _taken_under(kind: str) -> set[str]:
    """Return the examples of a value taken that the 409 of a kind of write cites."""
    cited: set[str] = set()
    for path in sorted((API / "paths").glob("*.yaml")):
        for block in path.read_text(encoding="utf-8").split("operationId: ")[1:]:
            if block.startswith(kind) and "\n      '409':" in block:
                said = block.split("\n      '409':", 1)[1].split("\n      '4", 1)[0]
                cited |= set(re.findall(r"fixtures/api/(\w+_taken)\.json", said))
    return cited


def test_a_value_taken_cited_at_the_creation_and_the_modification_says_both(
    examples: dict[str, Any],
) -> None:
    # The summary says what the example stands for, under each operation that serves it (revue 1).
    both = _taken_under("create") & _taken_under("update")
    assert {"org_node_code_taken", "resource_role_code_taken", "calendar_label_taken"} <= both
    for name in both:
        summary = examples[name]["summary"]
        assert any(word in summary for word in ("créé", "création")), name
        assert any(word in summary for word in ("modifi", "renomm", "recod")), name


def test_every_category_bears_an_accounting_code_of_its_own() -> None:
    listed = list(_categories().values())
    for category in listed:
        code = category["accounting_code"]
        assert isinstance(code, str), category["code"]
        assert 1 <= len(code) <= 20, category["code"]
    for field in ("code", "accounting_code"):
        assert len({category[field] for category in listed}) == len(listed), field
    by_id = _categories()
    for name in ("cost_category_updated", "cost_category_deactivated"):
        written = fixture(name)
        assert written["accounting_code"] == by_id[written["cost_category_id"]]["accounting_code"]
    # The category created today takes a code and an accounting code no other bears.
    created = fixture("cost_category_created")
    assert created["cost_category_id"] not in by_id
    for field in ("code", "accounting_code"):
        assert created[field] not in {category[field] for category in listed}, field


# --- The refusals by field of a nature or a category -------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "cost_type_creation_refused",
        "cost_type_update_refused",
        "cost_category_creation_refused",
        "cost_category_update_refused",
    ],
)
def test_a_write_of_the_cost_settings_is_refused_field_by_field(name: str) -> None:
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert "params" not in refused
    fields = refused["fields"]
    assert fields
    for field in fields:
        assert field["code"] in REFUSALS[field["pointer"]], name
        assert "params" not in field, name
    if name.startswith("cost_type"):
        assert all(field["pointer"] in TEXTS - {"/accounting_code"} for field in fields), name


@pytest.mark.parametrize("name", sorted(TOLD))
def test_each_refusal_tells_its_fields_and_motives_as_its_summary_says(
    examples: dict[str, Any], name: str
) -> None:
    refused, summary = examples[name]["value"], examples[name]["summary"]
    status, code, fields, params = TOLD[name]
    assert (refused["status"], refused["code"]) == (status, code)
    assert [(field["pointer"], field["code"]) for field in refused.get("fields", [])] == fields
    assert refused.get("params", {}) == params
    for said in SAID[name]:
        assert said in summary, said


def test_every_refusal_told_has_what_its_summary_says() -> None:
    assert SAID.keys() == TOLD.keys()


def test_the_rate_refused_is_below_the_minimum_its_refusal_names(examples: dict[str, Any]) -> None:
    example = examples["hourly_rate_amount_refused"]
    [field] = example["value"]["fields"]
    found = re.search(r"corrigé à (-?\d+),(\d{2})", example["summary"])
    assert found is not None
    assert Decimal(f"{found[1]}.{found[2]}") < Decimal(field["params"]["minimum"])


def unsaid_reading(text: str, operations: tuple[str, ...]) -> list[str]:
    """Return the operations of a file of paths whose description does not say to read anew."""
    missing: list[str] = []
    for operation in operations:
        block = text.split(f"operationId: {operation}\n", 1)[1].split("\n    responses:", 1)[0]
        if "relit" not in block:
            missing.append(operation)
    return missing


def test_each_write_that_changes_other_commands_says_the_client_reads_the_lists_anew() -> None:
    text = (API / "paths" / "reference.yaml").read_text(encoding="utf-8")
    assert unsaid_reading(text, RELIT) == []
    probe = "    operationId: a\n    description: le client relit.\n    responses:\n"
    probe += "    operationId: b\n    description: rien.\n    responses:\n      relit\n"
    assert unsaid_reading(probe, ("a", "b")) == ["b"]


def test_the_categories_say_the_last_of_provision_deactivates_as_the_others(
    examples: dict[str, Any],
) -> None:
    summary = examples["volume/cost_categories"]["summary"]
    assert "la dernière de type provision pour risques comme les autres" in summary
    assert all(condition not in summary for condition in WITHDRAWN)


def max_length(text: str, schema: str, field: str) -> int:
    """Return the `maxLength` a schema of a file of the contract gives one of its fields."""
    block = text.split(f"\n{schema}:\n", 1)[1]
    block = re.split(r"\n(?=\S)", block, maxsplit=1)[0]
    lines = block.splitlines()
    [start] = [i for i, line in enumerate(lines) if line.startswith(f"    {field}:")]
    for line in lines[start:]:
        if line is not lines[start] and re.match(r"^    \S", line):
            break
        found = re.search(r"maxLength: (\d+)", line)
        if found is not None:
            return int(found[1])
    message = f"{schema}.{field} has no maxLength"
    raise ValueError(message)


@pytest.mark.parametrize("name", sorted(TOO_LONG))
def test_a_text_refused_too_long_is_longer_than_the_schema_admits(
    examples: dict[str, Any], name: str
) -> None:
    schema, field, length, said = TOO_LONG[name]
    text = (API / "components" / "schemas" / "reference.yaml").read_text(encoding="utf-8")
    assert length > max_length(text, schema, field)
    summary = examples[name]["summary"]
    assert f"{said} caractères" in summary
    if field == "code":
        # The code sent is in the summary, in capitals: it has the length told.
        words = [word.strip(",.;:()") for word in summary.split()]
        sent = [w for w in words if "-" in w and w.replace("-", "").isalpha() and w.isupper()]
        assert [len(word) for word in sent] == [length]


def test_the_schema_bounds_are_read_where_they_are_written() -> None:
    text = "A:\n  properties:\n    code: { type: string, maxLength: 20 }\n    label:\n"
    text += "      type: string\n      maxLength: 200\nB:\n  x: 1\n"
    assert max_length("\n" + text, "A", "code") == 20
    assert max_length("\n" + text, "A", "label") == 200


def _set_hourly_rate_examples() -> set[str]:
    """Return the fixtures the contract cites under `setHourlyRate`."""
    text = (API / "paths" / "reference.yaml").read_text(encoding="utf-8")
    block = text.split("operationId: setHourlyRate", 1)[1]
    return set(re.findall(r"fixtures/api/([a-z_]+)\.json", block))


def test_every_value_already_taken_names_its_fields_but_the_key_of_a_path(
    examples: dict[str, Any],
) -> None:
    taken = {
        name: example["value"]
        for name, example in examples.items()
        if isinstance(example["value"], dict)
        and cast("Entry", example["value"]).get("code") == "ALREADY_EXISTS"
    }
    keyed = _set_hourly_rate_examples()
    assert "hourly_rate_already_entered" in keyed
    assert len(taken) >= 4
    for name, refused in taken.items():
        assert refused["status"] == 409, name
        if name in keyed:
            assert "fields" not in refused, name
            continue
        assert refused["fields"], name
        for field in refused["fields"]:
            assert field["code"] == "ALREADY_EXISTS", name
            # The bearer by its identifier; by its label too for a project or a subproject, whose
            # form does not know the list that bears it (EP-14/L42i).
            assert list(field["params"]) in (
                ["conflicting_object_id"],
                ["conflicting_object_id", "conflicting_object_label"],
            ), name


UNIQUE = (
    ("reference.yaml", "createOrgNode", "/code"),
    ("reference.yaml", "updateOrgNode", "/code"),
    ("reference.yaml", "createResourceRole", "/code"),
    ("reference.yaml", "updateResourceRole", "/code"),
    ("reference.yaml", "createCalendar", "/label"),
    ("reference.yaml", "updateCalendar", "/label"),
    ("reference.yaml", "createCostType", "/code"),
    ("reference.yaml", "updateCostType", "/code"),
    ("reference.yaml", "createCostCategory", "/accounting_code"),
    ("reference.yaml", "updateCostCategory", "/accounting_code"),
    ("access.yaml", "createUser", "/email"),
    ("access.yaml", "updateUser", "/email"),
    ("revisions.yaml", "markRevision", "/version_name"),
    ("projects.yaml", "createProject", "/code"),
    ("projects.yaml", "updateProject", "/code"),
    ("projects.yaml", "createSubproject", "/code"),
    ("projects.yaml", "updateSubproject", "/code"),
)
"""The writes whose body bears a value unique among its objects, and that field: the uniqueness is
said in prose, so the table names them (EP-02/L42g, revue 3)."""


def conflict_said(text: str, operation: str) -> str:
    """Return the description of the 409 an operation of a file of paths declares in place."""
    block = text.split(f"operationId: {operation}\n", 1)[1].split("operationId:", 1)[0]
    found = re.search(r"\n      '409':\n(?P<said>(?:        .*\n|\n)+)", block)
    return "" if found is None else found["said"]


@pytest.mark.parametrize(("file", "operation", "pointer"), UNIQUE)
def test_each_write_of_a_unique_value_declares_its_409_and_the_field_it_names(
    file: str, operation: str, pointer: str
) -> None:
    said = conflict_said((API / "paths" / file).read_text(encoding="utf-8"), operation)
    assert "`ALREADY_EXISTS`" in said
    assert f"`{pointer}`" in said
    assert "conflicting_object_id" in said


def test_a_409_taken_from_the_shared_responses_says_nothing_of_its_own() -> None:
    text = "    operationId: a\n    responses:\n      '409': { $ref: x }\n"
    text += "    operationId: b\n    responses:\n      '409':\n        description: Dit.\n"
    assert conflict_said(text, "a") == ""
    assert "Dit." in conflict_said(text, "b")


def test_the_names_of_an_external_account_are_refused_by_its_origin(
    examples: dict[str, Any],
) -> None:
    example = examples["user_external_update_refused"]
    refused = example["value"]
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert set(refused) == {"code", "status", "correlation_id"}
    users = fixture("users")["items"]
    [named] = [u for u in users if f"{u['first_name']} {u['last_name']}" in example["summary"]]
    assert named["origin"] != "local"


# --- The hourly rates ---------------------------------------------------------------------------


def test_a_rate_is_refused_below_the_smallest_amount_that_every_rate_of_the_universe_reaches(
    examples: dict[str, Any],
) -> None:
    refused = fixture("hourly_rate_amount_refused")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    [field] = refused["fields"]
    assert (field["pointer"], field["code"]) == ("/amount", "VALUE_OUT_OF_RANGE")
    minimum = Decimal(field["params"]["minimum"])
    assert minimum == SMALLEST_RATE
    rates = [
        Decimal(entry["amount"])
        for example in examples.values()
        for entry in _walk(example["value"])
        if {"cost_category_id", "year", "amount"} <= entry.keys()
    ]
    assert len(rates) > 1000
    assert min(rates) >= minimum


def test_a_rate_is_refused_to_a_category_outside_labour_which_no_row_of_the_grid_is() -> None:
    refused = fixture("hourly_rate_non_labour_refused")
    assert (refused["status"], refused["code"]) == (422, "LABOUR_CATEGORY_REQUIRED")
    assert set(refused) == {"code", "status", "correlation_id"}
    categories = _categories()
    kinds = {nature["cost_type_id"]: nature["kind"] for nature in fixture("cost_types")["items"]}
    # The category the refusal speaks of, by its label, is one of the disbursements.
    summary = mockwitness.FIXTURES.joinpath("hourly_rate_non_labour_refused.json").read_text(
        encoding="utf-8"
    )
    told = json.loads(summary)["summary"].lower()
    [named] = [c for c in categories.values() if f"pour la {c['label'].lower()}," in told]
    assert kinds[named["cost_type_id"]] == "non_labor"
    for row in fixture("volume/hourly_rate_grid")["rows"]:
        assert kinds[categories[row["cost_category_id"]]["cost_type_id"]] == "labor", row["code"]


def test_a_second_rate_of_a_year_is_refused_where_the_grid_bears_one(
    examples: dict[str, Any],
) -> None:
    example = examples["hourly_rate_already_entered"]
    refused = example["value"]
    assert (refused["status"], refused["code"]) == (409, "ALREADY_EXISTS")
    assert set(refused) == {"code", "status", "correlation_id"}
    grid = fixture("volume/hourly_rate_grid")
    [mechanical] = [row for row in grid["rows"] if row["code"] == "MO-003"]
    cell = dict(zip(grid["years"], mechanical["cells"], strict=True))[2016]
    assert cell is not None
    # The rate the year already bears, as the summary says it.
    assert cell["amount"].replace(".", ",") in example["summary"]
    assert mechanical["label"].lower().split(" — ")[0] in example["summary"]


# --- One rule for every 412 ---------------------------------------------------------------------


def test_every_stale_version_refused_names_the_current_version_alone(
    examples: dict[str, Any],
) -> None:
    stale = {
        name: example["value"]
        for name, example in examples.items()
        if isinstance(example["value"], dict)
        and cast("Entry", example["value"]).get("code") == "STALE_LOCK_VERSION"
    }
    assert len(stale) >= 4
    for name, refused in stale.items():
        assert refused["status"] == 412, name
        assert set(refused) == {"code", "status", "params", "correlation_id"}, name
        assert list(refused["params"]) == ["expected_lock_version"], name
        assert refused["params"]["expected_lock_version"] >= 0, name


_BLOCK = re.compile(r"^(?P<indent> *)'412':(?P<rest>.*)$")


def stale_rules(text: str) -> list[int]:
    """Return the lines of a file of the contract where a 412 does not say the current version.

    A 412 declared in place says `STALE_LOCK_VERSION` and `params.expected_lock_version`; a 412
    taken from the shared responses says nothing of its own. A comment or a text that pairs 412
    with a parameter names `expected_lock_version`, and never `conflicting_object_id`.
    """
    lines = text.splitlines()
    wrong: list[int] = []
    for index, line in enumerate(lines):
        if "412" in line and "conflicting_object_id" in line:
            wrong.append(index + 1)
        found = _BLOCK.match(line)
        if found is None or "$ref" in found["rest"]:
            continue
        indent = len(found["indent"])
        block: list[str] = []
        for following in lines[index + 1 :]:
            if following.strip() and len(following) - len(following.lstrip()) <= indent:
                break
            block.append(following)
        said = " ".join(block)
        named = "STALE_LOCK_VERSION" in said and "params.expected_lock_version" in said
        if not named or "conflicting_object_id" in said:
            wrong.append(index + 1)
    return wrong


def test_every_412_of_the_contract_says_the_current_version() -> None:
    wrong = {
        path.relative_to(API).as_posix(): lines
        for path in CONTRACT
        if (lines := stale_rules(path.read_text(encoding="utf-8")))
    }
    assert wrong == {}
    assert API / "components" / "common.yaml" in CONTRACT
    shared = (API / "components" / "responses.yaml").read_text(encoding="utf-8")
    precondition = shared.split("PreconditionFailed:", 1)[1].split("\n\n", 1)[0]
    assert "params.expected_lock_version" in precondition


def test_a_412_that_does_not_say_the_current_version_is_found() -> None:
    text = (
        "    # 412 — périmé ; `params.conflicting_object_id`.\n"
        "      '412': { $ref: x }\n"
        "      '412':\n        description: >-\n          `STALE_LOCK_VERSION`, la version.\n"
        "      '422': { $ref: y }\n"
        "      '412':\n        description: >-\n          `STALE_LOCK_VERSION`,\n"
        "          `params.expected_lock_version` la version courante.\n"
    )
    assert stale_rules(text) == [1, 3]


def test_the_natures_read_with_the_deactivated_ones_have_the_disbursements_deactivated() -> None:
    # The universe has no deactivated nature: `cost_types_with_inactive` holds for the reading with
    # them alone, which the form of a category makes (EP-02/L42g) — the natures of the witness, the
    # disbursements as their deactivation answers them, the others untouched.
    deactivated = fixture("cost_type_deactivated")
    natures = fixture("cost_types")
    read = fixture("cost_types_with_inactive")
    assert read["meta"] == natures["meta"]
    assert read["items"] == [
        deactivated if nature["cost_type_id"] == deactivated["cost_type_id"] else nature
        for nature in natures["items"]
    ]
    assert [nature["is_active"] for nature in read["items"]] == [False, True, True]
