# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contributors of the project of the witness.

``contributors.json``: the list of ``project.json``, each with its kind, under the counter the
example gives it (``ContributorList.lock_version``: one version per inscription after the
creation). The accounts are those the slice of the projects created, a deactivated one listed all
the same; the platform is no author, so the creator is not inscribed by the creation but by this
list. Written through the interface of the projects, whose rules but those of a writer it keeps:
the accounts are known and the list holds a project manager.
"""

from typing import TYPE_CHECKING

from waterfall.api.contract.models import ContributorList, Project
from waterfall.core.projects.interface import (
    ContributorEntry,
    ContributorsLoad,
    contributors_present,
    load_contributors,
)
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

CONTRIBUTORS_FILE = "contributors.json"
PROJECT_FILE = "project.json"


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    project_id = witness.read(PROJECT_FILE, Project).project_id.root
    described = witness.read(CONTRIBUTORS_FILE, ContributorList)
    entries = tuple(
        ContributorEntry(item.user_id.root, item.kind.value) for item in described.items
    )
    imposed = {entry.user_id for entry in entries}
    if is_loaded(imposed, contributors_present(session, project_id, imposed)):
        return False
    counter = 0 if described.lock_version is None else described.lock_version.root
    load_contributors(session, ContributorsLoad(project_id, entries, counter))
    return True
