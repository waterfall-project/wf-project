# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks and the structures of the witness, written for the loader (US-2650/L1).

``witness_risks.json`` and ``witness_structures.json`` (``wftools.mockwitnessrisksfile``): what the
back loads, said once from the descriptions the examples are read from — the register of
``mockwitnessrisks``, the own estimates, the nodes the occurrence of 752 grafts, the amendments.
"""

import json
from decimal import Decimal
from typing import Any

import pytest

from wftools import REPOSITORY, mockdata, mockwitnessrisks, paths
from wftools import mockwitnessrisksfile as module

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

FIXTURES = REPOSITORY / "fixtures" / "api"
NAMES = (module.RISKS_NAME, module.STRUCTURES_NAME)


def _read(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["value"]


@pytest.mark.parametrize("name", NAMES)
def test_the_files_are_held_by_the_check_of_make_mock_data_up_to_date(name: str) -> None:
    assert name in mockdata.named()
    assert name in mockdata.declared_names()
    assert (FIXTURES / name).read_text(encoding="utf-8") == mockdata.render(mockdata.named()[name])
    declared = [entry for entry in paths.read().generated if f"fixtures/api/{name}" in entry.paths]
    assert [entry.by for entry in declared] == ["make mock-data"]


@pytest.mark.parametrize("name", NAMES)
def test_two_engenderings_give_the_same_bytes(name: str) -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. »
    assert mockdata.render(module.examples()[name]) == mockdata.render(module.examples()[name])


def test_the_risks_are_the_register_in_the_order_of_their_declaration() -> None:
    # Each declared at the probability of its first review, its provision line under a lineage the
    # 101 gives it, copied under the identifier the examples read in the 102.
    risks = _read(module.RISKS_NAME)["risks"]
    assert [each["label"] for each in risks] == [each.label for each in mockwitnessrisks.REGISTER]
    for risk, described in zip(risks, mockwitnessrisks.REGISTER, strict=True):
        assert Decimal(risk["probability"]) == described.reviews[0].probability
        line = described.reference_provision_line
        assert line is not None
        assert risk["provision_node_id"].endswith(f"{line:012d}")
        assert risk["provision_lineage_id"].endswith(f"{line + 100:012d}")
        assert [each["revision"] for each in risk["structures"]] == [101, 102]


def test_each_own_estimate_totals_the_severity_its_identification_retained() -> None:
    # The severity of a risk is the total of its own estimate (WF-RIS-0010): its declaration keeps
    # an own estimate still empty, its identification the one entered; 751 is raised to 1 250 000
    # in the 102 by its review of 2 February.
    risks = {each["label"]: each for each in _read(module.RISKS_NAME)["risks"]}
    for described in mockwitnessrisks.REGISTER:
        first = risks[described.label]["estimates"][0]
        total = sum(
            Decimal(line["quantity"]) * Decimal(line["unit_disbursement"])
            for line in first["lines"]
        )
        assert described.reviews[0].severity == 0
        assert total == described.reviews[1].severity, described.label
    rework = risks[mockwitnessrisks.REWORK.label]["estimates"]
    assert [each["revision"] for each in rework] == [101, 102]
    raised = sum(Decimal(line["unit_disbursement"]) for line in rework[1]["lines"])
    assert raised == mockwitnessrisks.REWORK.last.severity


def test_the_occurrence_grafts_the_nodes_the_examples_read_under_their_lineages() -> None:
    risks = {each["label"]: each for each in _read(module.RISKS_NAME)["risks"]}
    grafted = risks[mockwitnessrisks.DELIVERY_DELAY.label]["grafted"]
    items = _read("nodes_risk_occurred.json")["items"]
    assert {each["node_id"]: each["copy_lineage_id"] for each in grafted} == {
        each["node_id"]: each["lineage_id"] for each in items
    }
    others = [
        each for label, each in risks.items() if label != mockwitnessrisks.DELIVERY_DELAY.label
    ]
    assert all(not each["grafted"] for each in others)


def test_the_amendment_1_takes_the_reference_whole_and_the_amendment_2_its_trials_resumed() -> None:
    structures = _read(module.STRUCTURES_NAME)
    first, second = structures["amendments"]
    assert (first["revision"], first["rows_of"], first["tasks"], first["removed"]) == (
        101,
        101,
        [],
        [],
    )
    assert (second["revision"], second["rows_of"]) == (101, 102)
    assert [each["structure_id"][-3:] for each in second["copies"]] == ["203"]
    assert [each["label"] for each in second["tasks"]] == [
        "Installation sur site",
        "Essais sur site",
        "Reprise des essais de câblage",
        "Mise en service",
    ]
    assert len(second["removed"]) == 1
    assert [each["structure_id"][-3:] for each in structures["main"]] == ["211", "201"]
