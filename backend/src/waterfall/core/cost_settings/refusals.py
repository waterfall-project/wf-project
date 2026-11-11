# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusal of a single row the bootstrap has not written (WF-EXP-0040).

The settings and the mapping of the actual costs are each a row the bootstrap writes; an
installation migrated without running it again lacks them, and is not ready to serve: the
routes that read them say so (503), as the installation itself does, and not by an internal
error.
"""

from waterfall.platform.errors import UnavailableError
from waterfall.platform.installation import COMPONENT_UNAVAILABLE
from waterfall.platform.logs import get_logger

logger = get_logger(__name__)

# What the bootstrap writes, by the name the log gives.
REFERENCE_SETTINGS = "reference_settings"
ACTUAL_COST_MAPPING = "actual_cost_mapping"


def not_bootstrapped(missing: str) -> UnavailableError:
    """Log what the bootstrap has not written, and give the refusal (503, the database)."""
    logger.warning("cost_settings.not_bootstrapped", missing=missing)
    return UnavailableError(COMPONENT_UNAVAILABLE, {"component": "database"})
