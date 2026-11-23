# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The own estimate of a risk born whole, with its base, and made up to date for the witness.

The declaration of a risk creates its own estimate as a differential of the main structure (EP-30,
"La recomposition, la mise à jour et l'élagage"): the structure and its base, both of the start and
of the dates of the main structure, the own estimate keeping the counter of the main structure read
(``create_own_estimate``); the planning copies the main structure into each
(``open_own_estimate``). The loader of the witness, which copies the main structure into them again
until the update serves it (US-3090, US-3150), makes the own estimate retain the counter of the main
structure (``own_estimate_retained``).

Written by US-3070/L3; moved out of ``structures``, which a source file of a thousand lines stops.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from waterfall.core.revisions.interface.shared import BASE, MAIN, RISK
from waterfall.core.revisions.interface.structures import FIRST_VERSION, OpenedDifferential
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface.structures import StructureFacts
    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class OwnEstimateKept:
    """An own estimate created under an identifier given: the witness's, or one created again.

    ``structure_id`` its identifier; ``planning_start_on`` and ``main_lock_version`` the start and
    the counter of the main structure it kept, which the undoing of the deletion of its risk, or
    the redoing of its declaration, gives back (US-2590/L2), none to take the main structure's;
    ``base_id`` the identifier of its base, which the nodes kept of it name, none to draw it.
    """

    structure_id: UUID
    planning_start_on: date | None = None
    main_lock_version: int | None = None
    base_id: UUID | None = None


def create_own_estimate(
    session: Session,
    revision: tuple[UUID, UUID],
    risk: tuple[UUID, str],
    born: tuple[StructureFacts, OwnEstimateKept | None],
    act: Act,
) -> OpenedDifferential:
    """Create the structures of the own estimate of a risk and of its base, without nodes (EP-30).

    ``revision`` is the project and its current revision, ``risk`` the risk and its label, ``born``
    the facts of the main structure, read under its lock, and what the creation keeps. The own
    estimate is born whole, a differential of the main structure (EP-30, "Les états d'un devis
    propre"): the planning copies the nodes of the main structure into it and into its base once
    they exist (``open_own_estimate``). Both start their planning on
    the day the main structure does, which is the own estimate's (WF-RIS-0030), and hold its dates
    as it computed them; the own estimate keeps the counter of the main structure read, up to date
    while the main structure bears it. ``kept`` the identifier of an own estimate the witness
    imposes, or of one deleted with its risk, which the undoing of the deletion, or the redoing of
    the declaration, creates again (US-2590/L2), its start, its counter and its base with it.
    """
    (project_id, revision_id), (risk_id, label), (main, kept) = revision, risk, born
    structure_id = new_id() if kept is None else kept.structure_id
    base_id = new_id() if kept is None or kept.base_id is None else kept.base_id
    start = main.planning_start_on
    counter = main.lock_version
    if kept is not None:
        start = kept.planning_start_on or start
        counter = counter if kept.main_lock_version is None else kept.main_lock_version
    for each, kind, differential in ((structure_id, RISK, None), (base_id, BASE, structure_id)):
        session.add(
            CostStructure(
                project_id=project_id,
                id=each,
                revision_id=revision_id,
                kind=kind,
                label=label,
                is_merged=False,
                lineage_id=each,
                risk_id=risk_id if kind == RISK else None,
                differential_id=differential,
                main_lock_version=counter if kind == RISK else None,
                planning_start_on=start,
                scheduled_at=main.scheduled_at,
                lock_version=FIRST_VERSION,
                created_at=act.at,
                created_by=act.author,
                updated_at=act.at,
                updated_by=act.author,
            )
        )
        # The base names its own estimate, which is written first.
        session.flush()
    return OpenedDifferential(structure_id, base_id)


def own_estimate_retained(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Make the own estimate of a risk retain the counter its main structure bears now (EP-30).

    For the loader of the witness, which copies the main structure into it and its base again
    (``load_own_estimate_again``): up to date, as its update leaves it (US-3090). To be called
    under the lock of the main structure.
    """
    revision_id = session.scalar(
        select(CostStructure.revision_id).where(
            CostStructure.project_id == project_id, CostStructure.id == structure_id
        )
    )
    session.execute(
        update(CostStructure)
        .where(
            CostStructure.project_id == project_id,
            CostStructure.id == structure_id,
            CostStructure.kind == RISK,
        )
        .values(
            main_lock_version=select(CostStructure.lock_version)
            .where(
                CostStructure.project_id == project_id,
                CostStructure.revision_id == revision_id,
                CostStructure.kind == MAIN,
            )
            .scalar_subquery()
        )
        .execution_options(synchronize_session=False)
    )
    for held in tuple(session.identity_map.values()):
        if isinstance(held, CostStructure) and held.id == structure_id:
            session.expire(held, ["main_lock_version"])
