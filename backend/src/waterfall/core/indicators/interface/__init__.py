# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the indicators (FBS-4.8) offer to the API, the worker, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Every function the design names (EP-10,
"Modules") is declared from US-1660/L1 on: it raises ``NotImplementedError`` naming the story that
fills it. A name a story
adds besides joins the import of its file, below the comment that names it. Another module imports
them from here, never from the file; no module of the domain imports this one, which reads the
interfaces of the estimate, the actual costs, the planning, the revisions, the projects and the
settings.

The indicators fill, at the import of this interface, ``register_indicators`` of the revisions:
``store_indicators``, which keeps the indicators of a revision in the transaction of its marking
(US-1670/L1); and ``register_physical_progress`` of the planning: ``physical_progress``, the
physical progress of the summaries a reading of a structure gives (US-1680). The entry points
that mark a revision — the API, the loader of the witness, which marks by ``load_marking``, and the
worker, which imports it from US-1670/L1 on (EP-10, "Le worker") — import it (#2180).
"""

# ``curves`` (US-1660/L1; US-1690/L2, US-1690/L3): the cumulative costs, the earned value curves.
from waterfall.core.indicators.interface.curves import (
    cost_curve as cost_curve,
)
from waterfall.core.indicators.interface.curves import (
    earned_value_curves as earned_value_curves,
)

# ``documents`` (US-1660/L1): the documents a reading answers and a marking keeps, and their kinds.
from waterfall.core.indicators.interface.documents import (
    Document as Document,
)
from waterfall.core.indicators.interface.documents import (
    IndicatorKind as IndicatorKind,
)

# ``estimate_documents`` (US-1670/L1): the indicators of an estimate and of the remaining to commit
# as the contract writes them, which the API answers and a marking keeps.
from waterfall.core.indicators.interface.estimate_documents import (
    estimate_document as estimate_document,
)
from waterfall.core.indicators.interface.estimate_documents import (
    missing_rate_document as missing_rate_document,
)
from waterfall.core.indicators.interface.estimate_documents import (
    remaining_document as remaining_document,
)

# ``index_history`` (US-1660/L1; US-1700): the evolution of the indices.
from waterfall.core.indicators.interface.index_history import (
    index_history as index_history,
)

# ``milestone_tracking`` (US-1660/L1; US-1710): the time/time diagram.
from waterfall.core.indicators.interface.milestone_tracking import (
    milestone_tracking as milestone_tracking,
)

# ``physical_progress`` (US-1660/L1; US-1680): the physical progress of the summary tasks.
from waterfall.core.indicators.interface.physical_progress import (
    physical_progress as physical_progress,
)

# ``project_indicators`` (US-1660/L1; US-1660/L3, US-1670/L2): the indicators of a project, and
# what a reading of the current day computes on (``day_reading``, read by the curves, US-1690/L2;
# ``current_day_reading``, by the time/time diagram, US-1710; ``day_indicators``, from the cache of
# the day, US-1720/L2).
from waterfall.core.indicators.interface.project_indicators import (
    DayReading as DayReading,
)
from waterfall.core.indicators.interface.project_indicators import (
    current_day_reading as current_day_reading,
)
from waterfall.core.indicators.interface.project_indicators import (
    day_indicators as day_indicators,
)
from waterfall.core.indicators.interface.project_indicators import (
    day_reading as day_reading,
)
from waterfall.core.indicators.interface.project_indicators import (
    project_indicators as project_indicators,
)

# ``reading`` (US-1660/L1): what a reading asks, its revision, its scope and its instant.
from waterfall.core.indicators.interface.reading import (
    IndicatorsReading as IndicatorsReading,
)

# ``stored_documents`` (US-1660/L1; US-1670/L1; US-1690/L3; US-1710; US-1720/L2): a document a
# marked revision kept, whether it kept its kind, the marked revision a reading of a marking reads,
# and those that kept the project.
from waterfall.core.indicators.interface.stored_documents import (
    KeptOfKind as KeptOfKind,
)
from waterfall.core.indicators.interface.stored_documents import (
    kept_of_kind as kept_of_kind,
)
from waterfall.core.indicators.interface.stored_documents import (
    kept_revision as kept_revision,
)
from waterfall.core.indicators.interface.stored_documents import (
    kept_revisions as kept_revisions,
)
from waterfall.core.indicators.interface.stored_documents import (
    revisions_keeping_project as revisions_keeping_project,
)
from waterfall.core.indicators.interface.stored_documents import (
    stored_document as stored_document,
)

# ``storing`` (US-1660/L1; US-1670/L1): what a revision keeps at its marking.
from waterfall.core.indicators.interface.storing import (
    store_indicators as store_indicators,
)

# The registries the indicators fill.
from waterfall.core.planning.interface import register_physical_progress
from waterfall.core.revisions.interface import register_indicators

# The registrations, once, at the import: what a marking keeps of the indicators (US-1670/L1), and
# the physical progress of the summaries a reading of a structure gives (US-1680).
register_indicators(store_indicators)
register_physical_progress(physical_progress)
