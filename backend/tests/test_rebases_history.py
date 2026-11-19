# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The update of a differential and the history, the other differentials, the witness (US-3050/L4).

The update is outside the undoable history: it enters no entry of the stacks, nor the journal; an
entry of the differential made before it is undone, except on a node it wrote, where the undo is
refused naming the object (409 ``UNDO_CONFLICT``, WF-IHM-0110). Another differential of the
revision, and its state, are as they were. The function of the update offered to the loader of the
witness (``load_rebase``) writes what the confirmed update writes, with no report. Every answer is
checked against the contract (``ContractClient``).
"""

from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from amendments_support import (
    OWN_RENAMED,
    OutOfDate,
    node_labelled,
    on,
    opened_amendment,
    out_of_date,
)
from estimate_support import Costing, Lines, costing
from history_support import undo, undone
from nodes_support import entries, signed_in
from projects_support import Scene
from projects_support import scene as make_scene
from rebases_support import marks, outline, read_report, rebased, state_of
from risks_support import MAKING, STUDY, Costed, costed
from sqlalchemy import func, select

from waterfall.core.planning.interface import load_rebase
from waterfall.core.planning.writing import Place
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


def journal(stage: Scene) -> int:
    """Count the inscriptions of the journal."""
    with stage.database.transaction() as session:
        return session.scalar(select(func.count()).select_from(AuditEntry)) or 0


# --- The history ----------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["task", "line"])
@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_entry_before_the_update_is_undone_but_on_a_node_the_update_wrote(
    api: ContractClient, project: Costed, realm: TestRealm, kind: str
) -> None:
    # « la mise à jour n'entre pas à l'historique annulable ; une saisie du différentiel faite avant
    # elle s'annule encore, sauf sur un nœud qu'elle a écrit, où l'annulation est refusée en
    # nommant l'objet »: an entry on a node the update carries a value into — Étude, renamed by the
    # main structure; Fabrication, re-estimated — is refused naming it; the entry made after it, on
    # a node the update did not write — Formation, before the task it inserts — is undone first,
    # as before. Neither the stack nor the journal received the update.
    who = signed_in(project.stage, realm)
    late = out_of_date(api, project)
    own = late.amendment
    if kind == "task":
        written = node_labelled(own, STUDY)
        assert own.change(written, who, description="Gabarit").status_code == 200
    else:
        written = node_labelled(own, "Fabrication")
        assert Lines(own).change(written, who, quantity="2").status_code == 200
    spared = node_labelled(own, OWN_RENAMED[1])
    assert own.change(spared, who, label="Équipes formées").status_code == 200
    held = [(each.id, each.rank, each.undone) for each in entries(project.stage)]
    inscriptions = journal(project.stage)
    assert len(held) == 2
    assert rebased(api, late).status_code == 200
    assert [(each.id, each.rank, each.undone) for each in entries(project.stage)] == held
    assert journal(project.stage) == inscriptions
    first = undone(own, who)
    assert first["undone"]["node_ids"] == [spared["node_id"]]
    assert node_labelled(own, OWN_RENAMED[1])["difference"] == "modified"
    refused = undo(own, who)
    assert refused.status_code == 409, refused.text
    body = refused.json()
    assert body["code"] == "UNDO_CONFLICT"
    assert body["params"]["conflicting_object_id"] == written["node_id"]
    assert [(each.id, each.rank, each.undone) for each in entries(project.stage)] == [
        (held[0][0], held[0][1], False),
        (held[1][0], held[1][1], True),
    ]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_entry_on_a_node_the_update_leaves_as_it_is_is_undone_after_it(
    api: ContractClient, project: Costed, realm: TestRealm
) -> None:
    # « une saisie du différentiel faite avant elle s'annule encore »: the entries on nodes the
    # update does not write — Réalisation and the task the differential renamed, both before the
    # task it inserts — are undone one after the other, the last first, after the update.
    who = signed_in(project.stage, realm)
    late = out_of_date(api, project)
    own = late.amendment
    for label, change in ((MAKING, "Réalisation 2"), (OWN_RENAMED[1], "Équipes formées")):
        assert own.change(node_labelled(own, label), who, label=change).status_code == 200
    assert rebased(api, late).status_code == 200
    first, second = (undone(own, who)["undone"]["node_ids"] for _ in range(2))
    assert first == [node_labelled(own, OWN_RENAMED[1])["node_id"]]
    assert second == [node_labelled(own, MAKING)["node_id"]]
    assert marks(own)[OWN_RENAMED[1]] == "modified"


# --- The other differentials ----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_another_differential_of_the_revision_and_its_state_are_unchanged(
    api: ContractClient, project: Costed
) -> None:
    # « un autre différentiel de la révision et son état sont inchangés »: a second differential,
    # out of date too, keeps its nodes, its counter, its state and its own report.
    second = opened_amendment(api, project, "Avenant 2")
    late = out_of_date(api, project)
    other = OutOfDate(project, second, on(project.tree, second))
    held = (
        state_of(api, project, second),
        other.amendment.read().json(),
        read_report(api, other),
    )
    assert held[0]["is_up_to_date"] is False
    assert rebased(api, late).status_code == 200
    assert (
        state_of(api, project, second),
        other.amendment.read().json(),
        read_report(api, other),
    ) == held
    assert state_of(api, project, late.structure_id)["is_up_to_date"] is True


# --- The witness ----------------------------------------------------------------------------------


def loaded(late: OutOfDate) -> None:
    """Update a differential as the loader of the witness does: no report, no counters."""
    project = late.project
    place = Place(project.project_id, project.revision_id, UUID(late.structure_id))
    with project.stage.database.transaction() as session:
        load_rebase(session, place, Act(project.stage.manager.user_id, utc_now()))


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_function_offered_to_the_witness_updates_without_a_report(
    api: ContractClient, project: Costed
) -> None:
    # « la fonction de la mise à jour offerte au chargeur du témoin, sans compte rendu »: it writes
    # what the confirmed update writes — the same outline, the differential up to date — and a
    # differential already up to date is refused as its command is.
    late = out_of_date(api, project)
    loaded(late)
    assert state_of(api, project, late.structure_id)["is_up_to_date"] is True
    assert [(label, mark) for _, label, mark in outline(late.amendment)] == [
        ("Étude préalable", "unchanged"),
        ("Plans", "unchanged"),
        ("Réalisation", "unchanged"),
        ("Fabrication", "unchanged"),
        ("Montage", "removed"),
        ("Formation des équipes", "modified"),
        ("Recette", "unchanged"),
        ("Essais", "added"),
    ]
    with pytest.raises(ConflictError) as refused:
        loaded(late)
    assert refused.value.params == {"missing_condition": "structure_out_of_date"}
