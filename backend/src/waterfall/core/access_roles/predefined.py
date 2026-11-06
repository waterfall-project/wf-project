# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The three roles delivered with the platform, as the bootstrap creates them (WF-ADM-0010).

Their permissions are those the example ``access_roles`` of the contract delivers: the project
manager holds the permissions of WF-INTF-0010, the distinct ones of WF-ADM-0100 included but
"restore the platform" and "read all the projects"; the manager those of WF-INTF-0020; the
administrator those of WF-INTF-0030, the reading of the journal of audit included. Their labels are
in the default language of the installation, and modifiable afterwards as any label
(WF-EXP-0020). The account of the bootstrap holds the administrator.

Each permission of the catalogue declares besides whether it consults (``CONSULTATION``): the
evaluation of an action refuses a consultation missing as an unknown object (404), any other
permission missing by naming it (403) (WF-ADM-0110). A property of the code, not a column of the
catalogue: the catalogue changes only with the contract, and with it this declaration, which a test
holds to the catalogue the migrations write.
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
# Whether each permission of the catalogue consults, in the order of the catalogue. The suffix of a
# code does not tell it: ``all_projects_read`` consults, and opens a project to its holder that is
# no contributor (#754).
CONSULTATION: dict[str, bool] = {
    "users.read": True,
    "users.write": False,
    "access_roles.read": True,
    "access_roles.write": False,
    "system_status.read": True,
    "backups.read": True,
    "backups.write": False,
    "audit_log.read": True,
    "portfolio_projects.read": True,
    "portfolio_workload.read": True,
    "portfolio_performance.read": True,
    "portfolio_cost_structure.read": True,
    "portfolio_risks.read": True,
    "portfolio_cost_curve.read": True,
    "portfolio_pilot_health.read": True,
    "cost_settings.read": True,
    "cost_settings.write": False,
    "resource_settings.read": True,
    "resource_settings.write": False,
    "risk_settings.read": True,
    "risk_settings.write": False,
    "indicator_settings.read": True,
    "indicator_settings.write": False,
    "revisions.read": True,
    "revisions.write": False,
    "project_settings.read": True,
    "project_settings.write": False,
    "planning.read": True,
    "planning.write": False,
    "estimate.read": True,
    "estimate.write": False,
    "remaining.read": True,
    "remaining.write": False,
    "risks.read": True,
    "risks.write": False,
    "actual_costs.read": True,
    "actual_costs.write": False,
    "project_indicators.read": True,
    "project_indicators.write": False,
    "lifecycle.read": True,
    "lifecycle.write": False,
    "revision_mark": False,
    "revision_abandon": False,
    "reference_designate": False,
    "structure_merge": False,
    "project_exit": False,
    "risk_occurrence": False,
    "cost_line_exclude": False,
    "platform_restore": False,
    "project_create": False,
    "all_projects_read": True,
}
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
