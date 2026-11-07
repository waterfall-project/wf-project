# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A role deprived of one permission stops the matching action (US-0900, WF-ADM-0020-A).

The role holds everything the predefined « manager » holds but ``resource_settings.write``: its
holder reads the roles of resources and is refused their creation. The positive counterpart of the
criterion (a role of ``cost_settings.write`` and ``users.write`` creates a nature and a local
account) is played by the course ``e2e/service/reference-manager.spec.ts``: creating an account
asks for the identity provider, which these tests do not run.
"""

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from access_rows import account, role
from realm import KEY
from support import bearer

from waterfall.core.access_roles.predefined import MANAGER

if TYPE_CHECKING:
    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

ROLES = "/api/v1/reference/resource-roles"
DEPRIVED = "resource_settings.write"
BE_ELEC = "01926f3a-7c00-7000-8000-000000000471"
INGENIERIE = "01926f3a-7c00-7000-8000-000000000402"
STANDARD = "01926f3a-7c00-7000-8000-000000000481"


@pytest.mark.requirement("WF-ADM-0020-A")
def test_a_role_with_all_of_the_manager_but_one_permission_reads_and_cannot_create(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # « Réciproquement, un rôle privé d'une permission empêche l'action correspondante, quel que
    # soit l'acteur auquel l'utilisateur ressemble. »
    kept = tuple(each for each in MANAGER if each != DEPRIVED)
    assert len(kept) == len(MANAGER) - 1
    held = role(witness, f"Manager sans {DEPRIVED}", permissions=kept)
    subject = f"subject-{uuid4()}"
    account(witness, "Durand", "Marc", roles=(held,), idp_subject=subject)
    headers = bearer(realm.token(subject, KEY))

    read = api.get(ROLES, headers=headers)
    assert read.status_code == 200, read.text
    assert read.json()["items"]

    sent = {
        "code": "DESS-ELEC",
        "label": "Dessinateur électricien",
        "org_node_id": BE_ELEC,
        "cost_category_id": INGENIERIE,
        "calendar_id": STANDARD,
        "capacity": {"monthly_hours": "520.00", "headcount": "3"},
    }
    refused = api.post(ROLES, headers=headers, json=sent)
    body = refused.json()
    assert (refused.status_code, body["code"]) == (403, "PERMISSION_MISSING")
    assert body["params"] == {"missing_permission": DEPRIVED}
