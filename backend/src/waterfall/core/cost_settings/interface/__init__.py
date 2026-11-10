# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the cost settings (FBS-3.1) offer to the API, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names
of a file are imported in a statement of their own, below the comment that names the file, so
that two stories filling two files write two places of this one. Another module imports them
from here, never from the file.
"""

# ``employment`` (US-1490/L1; the rates written, US-1500/L2): what the lines of an estimate tell,
# a private module the files of the categories and of the rates both read.
from waterfall.core.cost_settings.employment import (
    RateWritten as RateWritten,
)
from waterfall.core.cost_settings.employment import (
    register_employment as register_employment,
)

# ``records`` (US-1570/L5, #2615): the lock of the natures, which a write of a line of estimate
# shares before it locks its structure, in the order the rechiffrage takes them.
from waterfall.core.cost_settings.records import (
    share_natures as share_natures,
)

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
# ``cost_categories`` (US-0820; the lines that employ one, US-1490/L1): the categories of cost.
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
    categories_named as categories_named,
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
    read_cost_categories as read_cost_categories,
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
    cost_type_labels as cost_type_labels,
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
from waterfall.core.cost_settings.interface.hourly_rates import (
    GridColumn as GridColumn,
)
from waterfall.core.cost_settings.interface.hourly_rates import (
    HourlyRateFilters as HourlyRateFilters,
)
from waterfall.core.cost_settings.interface.hourly_rates import (
    HourlyRateGridPage as HourlyRateGridPage,
)
from waterfall.core.cost_settings.interface.hourly_rates import (
    HourlyRateRow as HourlyRateRow,
)
from waterfall.core.cost_settings.interface.hourly_rates import (
    HourlyRateSort as HourlyRateSort,
)
from waterfall.core.cost_settings.interface.hourly_rates import (
    HourlyRateView as HourlyRateView,
)

# ``hourly_rates`` (US-0830): the hourly rates of the categories of labour, by year.
from waterfall.core.cost_settings.interface.hourly_rates import (
    category_is_rated as category_is_rated,
)
from waterfall.core.cost_settings.interface.hourly_rates import (
    list_hourly_rates as list_hourly_rates,
)
from waterfall.core.cost_settings.interface.hourly_rates import (
    read_hourly_rate_grid as read_hourly_rate_grid,
)
from waterfall.core.cost_settings.interface.hourly_rates import (
    set_hourly_rate as set_hourly_rate,
)

# ``readiness`` (US-0810/L2): the questions of the minimal reference this module answers.
from waterfall.core.cost_settings.interface.readiness import (
    PREREQUISITES as PREREQUISITES,
)
from waterfall.core.cost_settings.interface.readiness import (
    labour_categories_exist as labour_categories_exist,
)
from waterfall.core.cost_settings.interface.readiness import (
    missing_prerequisites as missing_prerequisites,
)
from waterfall.core.cost_settings.interface.readiness import (
    provision_category_active as provision_category_active,
)

# ``reference_settings`` (US-0810/L2): the settings the installation shares.
from waterfall.core.cost_settings.interface.reference_settings import (
    DELIVERED_MATRIX as DELIVERED_MATRIX,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    DELIVERED_THRESHOLDS as DELIVERED_THRESHOLDS,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    DELIVERED_WEEKS as DELIVERED_WEEKS,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    FIELD_PERMISSIONS as FIELD_PERMISSIONS,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    IndexThresholds as IndexThresholds,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    ReferenceSettingsView as ReferenceSettingsView,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    RiskMatrix as RiskMatrix,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    SettingsChange as SettingsChange,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    company_name_faults as company_name_faults,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    install_reference_settings as install_reference_settings,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    read_reference_settings as read_reference_settings,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    reference_settings_installed as reference_settings_installed,
)
from waterfall.core.cost_settings.interface.reference_settings import (
    write_reference_settings as write_reference_settings,
)
