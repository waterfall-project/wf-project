# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The three roles delivered with the platform, as the bootstrap creates them (WF-ADM-0010).

Their permissions are those the example ``access_roles`` of the contract delivers: the project
manager holds the permissions of WF-INTF-0010, the distinct ones of WF-ADM-0100 included but
"restore the platform" and "read all the projects"; the manager those of WF-INTF-0020; the
administrator those of WF-INTF-0030, the reading of the journal of audit included. Their labels are
in the default language of the installation, and modifiable afterwards as any label
(WF-EXP-0020). The account of the bootstrap holds the administrator.
"""

from dataclasses import dataclass
from typing import Literal

type PredefinedKey = Literal["administrator", "project_manager", "manager"]

LABELS: dict[str, dict[PredefinedKey, str]] = {
    "fr": {
        "administrator": "Administrateur",
        "project_manager": "Chef de projet",
        "manager": "Manager",
    },
    "en": {
        "administrator": "Administrator",
        "project_manager": "Project manager",
        "manager": "Manager",
    },
}

ADMINISTRATOR = (
    "users.read",
    "users.write",
    "access_roles.read",
    "access_roles.write",
    "system_status.read",
    "backups.read",
    "backups.write",
    "audit_log.read",
    "platform_restore",
)
PROJECT_MANAGER = (
    "portfolio_projects.read",
    "cost_settings.read",
    "resource_settings.read",
    "risk_settings.read",
    "indicator_settings.read",
    *(
        f"{function}.{level}"
        for function in (
            "revisions",
            "project_settings",
            "planning",
            "estimate",
            "remaining",
            "risks",
            "actual_costs",
            "project_indicators",
            "lifecycle",
        )
        for level in ("read", "write")
    ),
    "revision_mark",
    "revision_abandon",
    "reference_designate",
    "structure_merge",
    "project_exit",
    "risk_occurrence",
    "cost_line_exclude",
    "project_create",
)
MANAGER = (
    "portfolio_projects.read",
    "portfolio_workload.read",
    "portfolio_performance.read",
    "portfolio_cost_structure.read",
    "portfolio_risks.read",
    "portfolio_cost_curve.read",
    "portfolio_pilot_health.read",
    "cost_settings.read",
    "cost_settings.write",
    "resource_settings.read",
    "resource_settings.write",
    "risk_settings.read",
    "indicator_settings.read",
    "revisions.read",
    "project_settings.read",
    "planning.read",
    "estimate.read",
    "remaining.read",
    "risks.read",
    "actual_costs.read",
    "project_indicators.read",
    "lifecycle.read",
    "all_projects_read",
)
PERMISSIONS: dict[PredefinedKey, tuple[str, ...]] = {
    "administrator": ADMINISTRATOR,
    "project_manager": PROJECT_MANAGER,
    "manager": MANAGER,
}


@dataclass(frozen=True, slots=True)
class PredefinedRole:
    """A role delivered with the platform: which one, its label, the codes of its permissions."""

    key: PredefinedKey
    label: str
    permissions: tuple[str, ...]


def predefined_roles(language: str) -> tuple[PredefinedRole, ...]:
    """Describe the three predefined roles, labelled in ``language``, one of the installation's."""
    labels = LABELS[language]
    return tuple(PredefinedRole(key, labels[key], codes) for key, codes in PERMISSIONS.items())
