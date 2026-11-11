# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mapping of the extraction of the actual costs (US-0870, WF-REF-0190), through the service.

The import that reads it is EP-09's: here, the mapping is declared, kept whole and read back, its
labels compared as the import will compare them. Every answer is checked against the contract.
"""

import json
from typing import TYPE_CHECKING, Any

import pytest
from installed_reference import install
from sqlalchemy import func, select
from support import WITNESS

from waterfall.core.cost_settings.interface import (
    ActualCostMappingWrite,
    ColumnLabels,
    create_actual_cost_mapping,
    fold_labels,
    read_actual_cost_mapping,
    read_folded_labels,
    replace_actual_cost_mapping,
)
from waterfall.core.cost_settings.refusals import (
    ACTUAL_COST_MAPPING,
    REFERENCE_SETTINGS,
    not_bootstrapped,
)
from waterfall.core.cost_settings.tables import ActualCostMapping
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import PreconditionFailedError, UnprocessableError
from waterfall.witness import actual_cost_mapping as witness_slice
from waterfall.witness.description import Witness

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from support import ContractClient, PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

PATH = "/api/v1/reference/actual-cost-mapping"
COLUMNS = ["wbs_element", "document_number", "document_item", "document_date", "amount"]
REQUIRED = ["wbs_element", "document_number", "document_date", "amount"]
DECLARED = {
    "wbs_element": ["Elément d'OTP"],
    "document_number": ["Nº pièce référence"],
    "document_date": ["Date de la pièce"],
    "amount": ["Val./Devise objet"],
}


@pytest.fixture
def mapping(database: Database) -> Database:
    """Give the database with the mapping the installation makes: empty, at its version 1."""
    with database.transaction() as session:
        create_actual_cost_mapping(session, Act(None, utc_now()))
    return database


@pytest.fixture
def installed(owner: Engine, database: Database) -> Database:
    """Give the database of an installation as its bootstrap leaves it: the mapping empty in it."""
    install(owner)
    return database


@pytest.fixture
def sessions(mapping: Database, reference_sessions: ReferenceSessions) -> PartSessions:
    """Give the three sessions of the cost settings, on a database that holds the mapping."""
    del mapping
    return reference_sessions("cost_settings")


def body(
    labels: dict[str, list[str]] | None = None, kept: list[str] | None = None, lock_version: int = 1
) -> dict[str, Any]:
    """Write the body of a replacement: the five columns in their order, the labels given."""
    given = labels or {}
    return {
        "columns": [{"column": name, "labels": given.get(name, [])} for name in COLUMNS],
        "kept_columns": kept or [],
        "lock_version": lock_version,
    }


def labels_of(answer: dict[str, Any]) -> dict[str, list[str]]:
    """Give the labels of each column of an answer."""
    return {column["column"]: column["labels"] for column in answer["columns"]}


@pytest.mark.requirement("WF-REF-0190-A")
def test_a_new_installation_has_an_empty_mapping_at_version_one_that_is_incomplete(
    api: ContractClient, sessions: PartSessions
) -> None:
    answer = api.get(PATH, headers=sessions.reading)
    assert answer.status_code == 200
    read = answer.json()
    assert [column["column"] for column in read["columns"]] == COLUMNS
    assert all(column["labels"] == [] for column in read["columns"])
    assert read["kept_columns"] == []
    assert (read["is_complete"], read["missing_columns"]) == (False, REQUIRED)
    assert read["lock_version"] == 1
    assert read["audit"]["created_by"] == {"kind": "platform"}


@pytest.mark.requirement("WF-REF-0190-A")
def test_a_declaration_is_kept_whole_with_its_counter_and_read_back(
    api: ContractClient, sessions: PartSessions
) -> None:
    written = api.put(
        PATH, json=body(DECLARED, ["Fournisseur", "Texte de commande"]), headers=sessions.changing
    )
    assert written.status_code == 200
    saved = written.json()
    assert labels_of(saved) == {**DECLARED, "document_item": []}
    assert saved["kept_columns"] == ["Fournisseur", "Texte de commande"]
    assert (saved["is_complete"], saved["missing_columns"], saved["lock_version"]) == (True, [], 2)
    assert saved["audit"]["updated_by"]["kind"] == "user"
    assert api.get(PATH, headers=sessions.reading).json() == saved


@pytest.mark.requirement("WF-REF-0190-A")
@pytest.mark.parametrize(
    ("sent", "pointer", "doubled"),
    [
        pytest.param(
            body({"wbs_element": ["Élément d'OTP", "élément d'otp  "]}),
            "/columns/0/labels/1",
            "/columns/0/labels/0",
            id="the-same-column",
        ),
        pytest.param(
            body({"wbs_element": ["Élément d'OTP"], "amount": ["ELEMENT D'OTP"]}),
            "/columns/4/labels/0",
            "/columns/0/labels/0",
            id="two-columns-read",
        ),
        pytest.param(
            body({"wbs_element": ["Élément d'OTP"]}, ["Fournisseur", "\télément d'otp"]),
            "/kept_columns/1",
            "/columns/0/labels/0",
            id="a-column-read-and-a-column-kept",
        ),
    ],
)
def test_a_label_that_doubles_another_once_compared_is_refused_and_nothing_is_written(
    api: ContractClient, sessions: PartSessions, sent: dict[str, Any], pointer: str, doubled: str
) -> None:
    refused = api.put(PATH, json=sent, headers=sessions.changing)
    assert refused.status_code == 422
    assert refused.json()["code"] == "VALIDATION_FAILED"
    assert refused.json()["fields"] == [
        {"pointer": pointer, "code": "DUPLICATE_COLUMN_LABEL", "params": {"duplicate_of": doubled}}
    ]
    kept_as_it_was = api.get(PATH, headers=sessions.reading).json()
    assert (kept_as_it_was["lock_version"], kept_as_it_was["is_complete"]) == (1, False)
    assert labels_of(kept_as_it_was) == {name: [] for name in COLUMNS}


@pytest.mark.requirement("WF-REF-0190-A")
def test_of_several_labels_that_double_one_each_names_the_first(
    api: ContractClient, sessions: PartSessions
) -> None:
    labels = {"wbs_element": ["OTP", "otp", "Otp"]}
    refused = api.put(PATH, json=body(labels, ["OTP "]), headers=sessions.changing)
    assert [(field["pointer"], field["params"]) for field in refused.json()["fields"]] == [
        ("/columns/0/labels/1", {"duplicate_of": "/columns/0/labels/0"}),
        ("/columns/0/labels/2", {"duplicate_of": "/columns/0/labels/0"}),
        ("/kept_columns/0", {"duplicate_of": "/columns/0/labels/0"}),
    ]


def test_a_label_declared_again_with_another_case_replaces_the_one_it_doubles(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The mapping is replaced whole: its former labels no longer count against the new ones.
    api.put(PATH, json=body({"wbs_element": ["Élément d'OTP"]}), headers=sessions.changing)
    again = api.put(
        PATH,
        json=body({"wbs_element": ["ÉLÉMENT D'OTP"]}, lock_version=2),
        headers=sessions.changing,
    )
    assert again.status_code == 200
    assert labels_of(again.json())["wbs_element"] == ["ÉLÉMENT D'OTP"]
    assert again.json()["lock_version"] == 3


def test_an_incomplete_mapping_is_kept_and_complete_once_the_four_required_columns_are_named(
    api: ContractClient, sessions: PartSessions
) -> None:
    partial = api.put(
        PATH,
        json=body({"document_number": ["Pièce"], "document_item": ["Poste"]}),
        headers=sessions.changing,
    )
    assert partial.status_code == 200
    assert partial.json()["missing_columns"] == ["wbs_element", "document_date", "amount"]
    only_required = api.put(PATH, json=body(DECLARED, lock_version=2), headers=sessions.changing)
    assert only_required.json()["is_complete"] is True
    assert labels_of(only_required.json())["document_item"] == []


def test_columns_that_are_not_the_five_once_each_in_their_order_are_refused_at_columns(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    swapped = body()
    swapped["columns"][0], swapped["columns"][1] = swapped["columns"][1], swapped["columns"][0]
    repeated = body()
    repeated["columns"][4] = repeated["columns"][0]
    missing = body()
    del missing["columns"][2]
    for sent in (swapped, repeated, missing):
        refused = api.put(PATH, json=sent, headers=headers)
        assert refused.status_code == 422
        assert [(f["pointer"], f["code"]) for f in refused.json()["fields"]] == [
            ("/columns", "VALIDATION_FAILED")
        ]


def test_more_than_twenty_labels_for_a_column_or_fifty_columns_kept_are_refused(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    many = [f"Intitulé {rank}" for rank in range(71)]
    refused = api.put(PATH, json=body({"amount": many[:21]}, many[:51]), headers=headers)
    assert refused.status_code == 422
    assert [(f["pointer"], f["code"], f["params"]) for f in refused.json()["fields"]] == [
        ("/columns/4/labels", "VALUE_TOO_LONG", {"max_length": 20}),
        ("/kept_columns", "VALUE_TOO_LONG", {"max_length": 50}),
    ]
    limit = api.put(PATH, json=body({"amount": many[:20]}, many[20:70]), headers=headers)
    assert limit.status_code == 200


@pytest.mark.parametrize(
    ("label", "code"),
    [("", "VALUE_REQUIRED"), ("x" * 201, "VALUE_TOO_LONG"), ("   ", "VALIDATION_FAILED")],
)
def test_a_label_that_is_empty_too_long_or_blank_is_refused_at_its_pointer(
    api: ContractClient,
    sessions: PartSessions,
    label: str,
    code: str,
) -> None:
    headers = sessions.changing
    refused = api.put(PATH, json=body({"document_date": ["Date", label]}), headers=headers)
    assert refused.status_code == 422
    assert [(f["pointer"], f["code"]) for f in refused.json()["fields"]] == [
        ("/columns/3/labels/1", code)
    ]


def test_reading_asks_for_the_permission_to_read_and_writing_for_the_one_to_change(
    api: ContractClient, sessions: PartSessions
) -> None:
    missing = api.get(PATH, headers=sessions.without)
    assert (missing.status_code, missing.json()["code"]) == (404, "NOT_FOUND")
    for headers in (sessions.without, sessions.reading):
        forbidden = api.put(PATH, json=body(DECLARED), headers=headers)
        assert (forbidden.status_code, forbidden.json()["code"]) == (403, "PERMISSION_MISSING")
        assert forbidden.json()["params"] == {"missing_permission": "cost_settings.write"}
    assert api.get(PATH, headers=sessions.changing).json()["lock_version"] == 1


def test_a_stale_counter_is_refused_with_the_current_one_and_nothing_is_written(
    api: ContractClient, sessions: PartSessions
) -> None:
    assert api.put(PATH, json=body(DECLARED), headers=sessions.changing).status_code == 200
    stale = api.put(PATH, json=body({"amount": ["Montant"]}), headers=sessions.changing)
    assert (stale.status_code, stale.json()["code"]) == (412, "STALE_LOCK_VERSION")
    assert stale.json()["params"] == {"expected_lock_version": 2}
    assert labels_of(api.get(PATH, headers=sessions.reading).json())["amount"] == DECLARED["amount"]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_mapping_is_loaded_over_the_empty_mapping_of_the_installation(
    api: ContractClient, installed: Database, reference_sessions: ReferenceSessions
) -> None:
    witness = Witness(WITNESS, Act(None, utc_now()))
    with installed.transaction() as session:
        assert witness_slice.load(session, witness) is True
    read = api.get(PATH, headers=reference_sessions("cost_settings").reading).json()
    assert (read["is_complete"], read["lock_version"]) == (True, 2)


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.parametrize(
    "writings",
    [
        # Emptied once, the mapping of the bootstrap written empty: its version 2 (#2096).
        [{}],
        # Declared, then emptied: its version 3.
        [DECLARED, {}],
    ],
)
def test_a_mapping_a_manager_emptied_is_held_and_the_witness_does_not_overwrite_it(
    api: ContractClient,
    installed: Database,
    sessions: PartSessions,
    writings: list[dict[str, list[str]]],
) -> None:
    for rank, labels in enumerate(writings, start=1):
        written = api.put(PATH, json=body(labels, lock_version=rank), headers=sessions.changing)
        assert written.json()["lock_version"] == rank + 1
    witness = Witness(WITNESS, Act(None, utc_now()))
    with installed.transaction() as session:
        assert witness_slice.load(session, witness) is False
    read = api.get(PATH, headers=sessions.reading).json()
    assert (read["is_complete"], read["lock_version"]) == (False, len(writings) + 1)
    assert all(not column["labels"] for column in read["columns"])


def test_the_witness_finds_no_mapping_on_a_database_the_bootstrap_has_not_installed(
    database: Database,
) -> None:
    # The bootstrap makes the mapping (#2092): the loader of the witness no longer does.
    witness = Witness(WITNESS, Act(None, utc_now()))
    with database.transaction() as session:
        assert witness_slice.load(session, witness) is False
        assert session.scalar(select(func.count()).select_from(ActualCostMapping)) == 0


def test_a_malformed_body_is_refused_422_before_its_stale_counter_is_refused_412(
    api: ContractClient, sessions: PartSessions
) -> None:
    sent = body({"amount": ["a"] * 21}, lock_version=9)
    refused = api.put(PATH, json=sent, headers=sessions.changing)
    assert (refused.status_code, refused.json()["code"]) == (422, "VALIDATION_FAILED")


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_mapping_is_loaded_in_the_form_of_the_contract_and_not_loaded_twice(
    api: ContractClient, installed: Database, reference_sessions: ReferenceSessions
) -> None:
    witness = Witness(WITNESS, Act(None, utc_now()))
    with installed.transaction() as session:
        assert witness_slice.load(session, witness) is True
        assert witness_slice.load(session, witness) is False
    read = api.get(PATH, headers=reference_sessions("cost_settings").reading).json()
    declared = witness.directory.joinpath("actual_cost_mapping.json").read_text(encoding="utf-8")
    expected = json.loads(declared)["value"]
    for name in ("columns", "kept_columns", "is_complete", "missing_columns", "lock_version"):
        assert read[name] == expected[name]


def test_labels_are_folded_without_case_accents_nor_spaces_at_their_ends(
    mapping: Database,
) -> None:
    with mapping.transaction() as session:
        assert fold_labels(session, []) == []
        assert fold_labels(session, ["  ÉLÉMENT d'OTP\t", "Nº pièce", "Poste "]) == [
            "element d'otp",
            "no piece",
            "poste",
        ]
        written = ActualCostMappingWrite(
            [ColumnLabels(name, DECLARED.get(name, [])) for name in COLUMNS], ["Fournisseur"]
        )
        replace_actual_cost_mapping(session, written, 1, Act(None, utc_now()))
        folded = read_folded_labels(session)
    assert folded == {
        "element d'otp": "wbs_element",
        "no piece reference": "document_number",
        "date de la piece": "document_date",
        "val./devise objet": "amount",
        "fournisseur": None,
    }


def test_the_interface_refuses_what_the_contract_would_not_let_through(mapping: Database) -> None:
    act = Act(None, utc_now())
    few = ActualCostMappingWrite([ColumnLabels("amount", [])], [])
    long = ActualCostMappingWrite(
        [ColumnLabels(name, ["a"] * 21 if name == "amount" else []) for name in COLUMNS],
        ["k"] * 51,
    )
    stale = ActualCostMappingWrite([ColumnLabels(name, []) for name in COLUMNS], [])
    with mapping.transaction() as session:
        for refused, pointers in (
            (few, ["/columns"]),
            (long, ["/columns/4/labels", "/kept_columns"]),
        ):
            with pytest.raises(UnprocessableError) as error:
                replace_actual_cost_mapping(session, refused, 1, act)
            assert [field.pointer for field in error.value.fields] == pointers
        with pytest.raises(PreconditionFailedError) as outdated:
            replace_actual_cost_mapping(session, stale, 7, act)
        assert dict(outdated.value.params) == {"expected_lock_version": 1}
        assert read_actual_cost_mapping(session).lock_version == 1


@pytest.mark.requirement("WF-EXP-0040-A")
def test_an_installation_without_the_row_of_the_mapping_refuses_to_read_and_to_replace_it(
    api: ContractClient,
    database: Database,
    reference_sessions: ReferenceSessions,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The bootstrap has not written the row: not ready to serve (503), as the settings are.
    sessions = reference_sessions("cost_settings")
    with database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(ActualCostMapping)) == 0
    for answer in (
        api.get(PATH, headers=sessions.reading),
        api.put(PATH, json=body(DECLARED), headers=sessions.changing),
    ):
        assert (answer.status_code, answer.json()["code"]) == (503, "COMPONENT_UNAVAILABLE")
        assert answer.json()["params"] == {"component": "database"}
    assert "missing=actual_cost_mapping" in capsys.readouterr().out
    with database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(ActualCostMapping)) == 0


@pytest.mark.requirement("WF-EXP-0040-A")
def test_the_refusal_of_a_row_not_written_names_it_in_the_log_for_each_of_the_two_rows(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for name, row in (
        ("reference_settings", REFERENCE_SETTINGS),
        ("actual_cost_mapping", ACTUAL_COST_MAPPING),
    ):
        refusal = not_bootstrapped(row)
        assert (refusal.code, dict(refusal.params)) == (
            "COMPONENT_UNAVAILABLE",
            {"component": "database"},
        )
        assert f"missing={name}" in capsys.readouterr().out
