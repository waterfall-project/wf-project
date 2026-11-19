# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risks (FBS-4.6) offer to the API, the worker, the other modules and the witness.

One file per subject, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Every function the design names (EP-08,
"Modules") — one by operation of the contract — is declared from US-2550/L1 on: it raises
``NotImplementedError`` naming the story that fills it. A name a story adds besides joins the
import of its file, below the comment that names it; a file a later epic adds (EP-11, the risks as
the portfolio reads them) takes a comment and imports of its own. Another module imports them from
here, never from the file.

The risks read the revisions, the planning, the estimate and the risk settings, none of which reads
them: what they must know of the risks goes through their registries, which the risks fill at the
import of this interface, each by the story that fills its part, below the imports — the copy and
the closing of a revision, and the counter of an own estimate (``register_copy``,
``register_closing``, ``register_own_estimate_counted``; US-2570/L1), the designation of
a reference and the coverage of the remaining to commit (``register_designation``,
``register_coverage``; US-2610/L1), the four kinds of entry of the history it undoes
(``register_undoable``; US-2590/L2). The entry points that open, close, mark or designate a revision
— the API, the worker, the loader of the witness — import this interface from US-2550/L1 on, so
that none lacks their part once a story registers it (#2180).
"""

# ``coverage`` (US-2550/L1; US-2610/L1): the reserve and the coverage of the risks.
# The registries the risks fill (US-2570/L1).
from waterfall.core.planning.interface import ProvisionOwners, register_provision_owners
from waterfall.core.revisions.interface import (
    register_closing,
    register_copy,
    register_own_estimate_counted,
)
from waterfall.core.risks.following import (
    close_evaluations,
    copy_evaluations,
    follow_own_estimate,
    follow_provision_lines,
    name_provision_owners,
)
from waterfall.core.risks.interface.coverage import (
    risk_coverage_of as risk_coverage_of,
)

# ``deletion`` (US-2550/L1; US-2590/L1): a risk deleted.
from waterfall.core.risks.interface.deletion import (
    RiskDeletion as RiskDeletion,
)
from waterfall.core.risks.interface.deletion import (
    delete_risk as delete_risk,
)

# ``matrix`` (US-2550/L1; US-2600/L2): the matrix of the risks of a project.
from waterfall.core.risks.interface.matrix import (
    risk_matrix as risk_matrix,
)

# ``occurrence`` (US-2550/L1; US-2620/L1, US-2620/L2): the occurrence of a risk.
from waterfall.core.risks.interface.occurrence import (
    OccurrenceReport as OccurrenceReport,
)
from waterfall.core.risks.interface.occurrence import (
    OccurrenceRequest as OccurrenceRequest,
)
from waterfall.core.risks.interface.occurrence import (
    occurrence_report as occurrence_report,
)
from waterfall.core.risks.interface.occurrence import (
    run_occurrence as run_occurrence,
)
from waterfall.core.risks.interface.occurrence import (
    submit_occurrence as submit_occurrence,
)

# ``provisions`` (US-2550/L1; US-2580/L1): the provision of an identified risk changed.
from waterfall.core.risks.interface.provisions import (
    RiskProvisionChange as RiskProvisionChange,
)
from waterfall.core.risks.interface.provisions import (
    update_risk_provision as update_risk_provision,
)

# ``register`` (US-2550/L1; US-2600/L1): the register of the risks.
from waterfall.core.risks.interface.register import (
    list_risks as list_risks,
)

# ``reviews`` (US-2550/L1; US-2590/L1): the reviews of a risk and the changes of its state.
from waterfall.core.risks.interface.reviews import (
    list_risk_reviews as list_risk_reviews,
)
from waterfall.core.risks.interface.reviews import (
    review_risk as review_risk,
)
from waterfall.core.risks.interface.risks import (
    create_risk as create_risk,
)
from waterfall.core.risks.interface.risks import (
    read_risk as read_risk,
)
from waterfall.core.risks.interface.risks import (
    update_risk as update_risk,
)
from waterfall.core.risks.views import (
    OMITTED as OMITTED,
)

# ``risks`` (US-2550/L1; US-2570/L1): a risk declared, read and renamed; ``register`` (US-2600/L1):
# what the register asks for and gives.
from waterfall.core.risks.views import (
    Bounds as Bounds,
)
from waterfall.core.risks.views import (
    MatrixCell as MatrixCell,
)
from waterfall.core.risks.views import (
    MatrixLevel as MatrixLevel,
)
from waterfall.core.risks.views import (
    MatrixPoint as MatrixPoint,
)
from waterfall.core.risks.views import (
    Omitted as Omitted,
)
from waterfall.core.risks.views import (
    ProvisionTask as ProvisionTask,
)
from waterfall.core.risks.views import (
    ProvisionTotals as ProvisionTotals,
)
from waterfall.core.risks.views import (
    RiskColumn as RiskColumn,
)
from waterfall.core.risks.views import (
    RiskCommand as RiskCommand,
)
from waterfall.core.risks.views import (
    RiskEntry as RiskEntry,
)
from waterfall.core.risks.views import (
    RiskFilters as RiskFilters,
)
from waterfall.core.risks.views import (
    RiskIdentityChange as RiskIdentityChange,
)
from waterfall.core.risks.views import (
    RiskList as RiskList,
)
from waterfall.core.risks.views import (
    RiskMatrix as RiskMatrix,
)
from waterfall.core.risks.views import (
    RiskMatrixCell as RiskMatrixCell,
)
from waterfall.core.risks.views import (
    RiskPage as RiskPage,
)
from waterfall.core.risks.views import (
    RiskReviewEntry as RiskReviewEntry,
)
from waterfall.core.risks.views import (
    RiskReviewView as RiskReviewView,
)
from waterfall.core.risks.views import (
    RiskSort as RiskSort,
)
from waterfall.core.risks.views import (
    RiskState as RiskState,
)
from waterfall.core.risks.views import (
    RiskView as RiskView,
)

# The registrations, once, at the import: the copy of the evaluations after the structures and the
# nodes whose copies they name, the interfaces of the revisions and of the planning imported first;
# their deletion at an abandonment before the nodes and the structures they name (``evaluations``);
# the counter and the provision of a risk following its own estimate (US-2570/L1), and the risks
# that own the provision lines a deletion or an import moves (US-2580/L1).
register_copy(copy_evaluations)
register_closing("evaluations", close_evaluations)
register_own_estimate_counted(follow_own_estimate)
register_provision_owners(ProvisionOwners(name_provision_owners, follow_provision_lines))
