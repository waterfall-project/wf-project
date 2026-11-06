# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the cost settings (FBS-3.1) offer to the API, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names
of a file are imported in a statement of their own, below the comment that names the file, so
that two stories filling two files write two places of this one. Another module imports them
from here, never from the file.
"""

# ``reference_settings`` (US-0810/L2): the settings the installation shares.

# ``readiness`` (US-0810/L2): the questions of the minimal reference this module answers.

# ``actual_cost_mapping`` (US-0870): the mapping of the extraction of the actual costs.
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    DUPLICATE_COLUMN_LABEL as DUPLICATE_COLUMN_LABEL,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    STALE_LOCK_VERSION as STALE_LOCK_VERSION,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    ActualCostMappingView as ActualCostMappingView,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    ActualCostMappingWrite as ActualCostMappingWrite,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    ColumnLabels as ColumnLabels,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    MappingColumn as MappingColumn,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    create_actual_cost_mapping as create_actual_cost_mapping,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    fold_labels as fold_labels,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    read_actual_cost_mapping as read_actual_cost_mapping,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    read_folded_labels as read_folded_labels,
)
from waterfall.core.cost_settings.interface.actual_cost_mapping import (
    replace_actual_cost_mapping as replace_actual_cost_mapping,
)

# ``cost_types`` (US-0820): the natures of cost.
# ``cost_categories`` (US-0820): the categories of cost.
from waterfall.core.cost_settings.interface.cost_categories import (
    CategoryLabel as CategoryLabel,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    CostCategoryDraft as CostCategoryDraft,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    CostCategoryFilters as CostCategoryFilters,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    CostCategoryPage as CostCategoryPage,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    CostCategorySort as CostCategorySort,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    CostCategoryView as CostCategoryView,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    category_is_employed as category_is_employed,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    category_label_of as category_label_of,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    category_labels as category_labels,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    create_cost_category as create_cost_category,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    list_cost_categories as list_cost_categories,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    present_cost_categories as present_cost_categories,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    set_cost_category_activation as set_cost_category_activation,
)
from waterfall.core.cost_settings.interface.cost_categories import (
    update_cost_category as update_cost_category,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypeDraft as CostTypeDraft,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypeFilters as CostTypeFilters,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypePage as CostTypePage,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypeSort as CostTypeSort,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypeView as CostTypeView,
)
from waterfall.core.cost_settings.interface.cost_types import (
    Page as Page,
)
from waterfall.core.cost_settings.interface.cost_types import (
    create_cost_type as create_cost_type,
)
from waterfall.core.cost_settings.interface.cost_types import (
    list_cost_types as list_cost_types,
)
from waterfall.core.cost_settings.interface.cost_types import (
    present_cost_types as present_cost_types,
)
from waterfall.core.cost_settings.interface.cost_types import (
    set_cost_type_activation as set_cost_type_activation,
)
from waterfall.core.cost_settings.interface.cost_types import (
    update_cost_type as update_cost_type,
)

# ``hourly_rates`` (US-0830): the hourly rates of the categories of labour, by year.
from waterfall.core.cost_settings.interface.hourly_rates import (
    category_is_rated as category_is_rated,
)
