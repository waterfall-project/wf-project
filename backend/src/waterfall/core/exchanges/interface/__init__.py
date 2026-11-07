# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the exchanges (FBS-4.3.4) offer to the API, the worker and the modules that serve a format.

One file per subject, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Another module imports them from here,
never from the file. The formats and the exporters are registered by the modules that serve them,
at the import of their interface (``register_format``, ``register_exporter``).
"""

# ``exports`` (US-1380/L1; US-1430/L2): the exporters, and the task that runs one.
from waterfall.core.exchanges.interface.exports import (
    Exporter as Exporter,
)
from waterfall.core.exchanges.interface.exports import (
    ExportKind as ExportKind,
)
from waterfall.core.exchanges.interface.exports import (
    exporters as exporters,
)
from waterfall.core.exchanges.interface.exports import (
    register_exporter as register_exporter,
)
from waterfall.core.exchanges.interface.exports import (
    run_export as run_export,
)

# ``imports`` (US-1380/L1; US-1420/L1): the formats, the analysis and the application.
from waterfall.core.exchanges.interface.imports import (
    ExchangeKind as ExchangeKind,
)
from waterfall.core.exchanges.interface.imports import (
    Format as Format,
)
from waterfall.core.exchanges.interface.imports import (
    formats as formats,
)
from waterfall.core.exchanges.interface.imports import (
    register_format as register_format,
)
from waterfall.core.exchanges.interface.imports import (
    run_analysis as run_analysis,
)
from waterfall.core.exchanges.interface.imports import (
    run_apply as run_apply,
)

# ``purge`` (US-1380/L1; US-1420/L2): the purge of the exchanges.
from waterfall.core.exchanges.interface.purge import (
    purge as purge,
)

# ``xml`` (US-1380/L1): the hardened reader of an XML file deposited, for every XML format.
from waterfall.core.exchanges.interface.xml import (
    hardened_parser as hardened_parser,
)
