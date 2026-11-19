# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio (FBS-2) offers to the API, the worker and the witness.

One file by view, and one for the scope and one for the contribution of a project, each filled by
the story that serves it and re-exported here: the names of a file are imported in a statement of
their own, below the comment that names the file, so that two stories filling two files write two
places of this one. Every function the design names (EP-11, "Modules") is declared from US-2670/L1
on: it raises ``NotImplementedError`` naming the story that fills it. A name a story adds besides
joins the import of its file, below the comment that names it. Another module imports them from
here, never from the file. A view answers the document of its operation, as the contract writes it.

The portfolio sits above every module of the domain, and none imports it: it reads the interfaces of
the indicators, the risks, the estimate, the actual costs, the planning, the revisions, the projects
and the settings. It fills, at the import of this interface, ``register_indicators`` of the
revisions: ``store_contribution``, after ``store_indicators``, which keeps the documents of the
portfolio of a revision in the transaction of its marking (US-2680/L2). The entry points that mark a
revision — the API, the worker and the loader of the witness — import it from US-2670/L1 on, so that
none lacks its part once that story registers it (#2180).
"""

# ``contribution`` (US-2670/L1; US-2680/L2, US-2680/L3): what a marking keeps for the portfolio.
from waterfall.core.portfolio.interface.contribution import (
    store_contribution as store_contribution,
)

# ``cost_curve`` (US-2670/L1; US-2740): the S-curve.
from waterfall.core.portfolio.interface.cost_curve import (
    read_portfolio_cost_curve as read_portfolio_cost_curve,
)

# ``cost_structure`` (US-2670/L1; US-2720): the structure of the costs.
from waterfall.core.portfolio.interface.cost_structure import (
    read_portfolio_cost_structure as read_portfolio_cost_structure,
)

# ``performance`` (US-2670/L1; US-2710): the indices, the projections, the quarters.
from waterfall.core.portfolio.interface.performance import (
    read_portfolio_performance as read_portfolio_performance,
)

# ``pilot_health`` (US-2670/L1; US-2750): the health of the control of the projects.
from waterfall.core.portfolio.interface.pilot_health import (
    read_pilot_health as read_pilot_health,
)

# ``projects`` (US-2670/L1; US-2690/L2): the list of the projects.
from waterfall.core.portfolio.interface.projects import (
    PortfolioListing as PortfolioListing,
)
from waterfall.core.portfolio.interface.projects import (
    read_portfolio_projects as read_portfolio_projects,
)

# ``risks`` (US-2670/L1; US-2730): the risks.
from waterfall.core.portfolio.interface.risks import (
    read_portfolio_risks as read_portfolio_risks,
)

# ``scope`` (US-2670/L1; US-2670/L3): what a view is asked and the scope it retains.
from waterfall.core.portfolio.interface.scope import (
    PortfolioAsked as PortfolioAsked,
)
from waterfall.core.portfolio.interface.scope import (
    PortfolioScope as PortfolioScope,
)
from waterfall.core.portfolio.interface.scope import (
    ResolvedScope as ResolvedScope,
)
from waterfall.core.portfolio.interface.scope import (
    RetainedProject as RetainedProject,
)
from waterfall.core.portfolio.interface.scope import (
    resolve_scope as resolve_scope,
)

# ``value`` (US-2670/L1; US-2690/L2): the order book, the pipeline, the delivered.
from waterfall.core.portfolio.interface.value import (
    read_portfolio_value as read_portfolio_value,
)

# ``workload`` (US-2670/L1; US-2700): the workload.
from waterfall.core.portfolio.interface.workload import (
    read_portfolio_workload as read_portfolio_workload,
)
