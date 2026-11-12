# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the exchanges (FBS-4.3.4) offer to the API, the worker and the modules that serve a format.

One file per subject, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Every function the design names (EP-06,
"Modules") is declared from US-1380/L1 on: it raises ``NotImplementedError`` naming the story that
fills it, but for those a caller relies on before (the purge), without effect until then. Another
module imports them from here, never from the file. The formats and the exporters are registered
by the modules that serve them, at the import of their interface (``register_format``,
``register_exporter``). The witness writes its imports as they ended (``load_import``, EP-09).
"""

# ``exports`` (US-1380/L1; US-1430/L2): the exporters, the task that runs one, and its result.
from waterfall.core.exchanges.interface.exports import (
    ExportAsked as ExportAsked,
)
from waterfall.core.exchanges.interface.exports import (
    ExportedFile as ExportedFile,
)
from waterfall.core.exchanges.interface.exports import (
    Exporter as Exporter,
)
from waterfall.core.exchanges.interface.exports import (
    ExportKind as ExportKind,
)
from waterfall.core.exchanges.interface.exports import (
    ExportOrder as ExportOrder,
)
from waterfall.core.exchanges.interface.exports import (
    ExportResult as ExportResult,
)
from waterfall.core.exchanges.interface.exports import (
    consumed as consumed,
)
from waterfall.core.exchanges.interface.exports import (
    exporters as exporters,
)
from waterfall.core.exchanges.interface.exports import (
    has_file as has_file,
)
from waterfall.core.exchanges.interface.exports import (
    register_exporter as register_exporter,
)
from waterfall.core.exchanges.interface.exports import (
    request_export as request_export,
)
from waterfall.core.exchanges.interface.exports import (
    result_of as result_of,
)
from waterfall.core.exchanges.interface.exports import (
    run_export as run_export,
)

# ``imports`` (US-1380/L1; US-1420/L1): the formats, the deposit, the analysis and the application.
from waterfall.core.exchanges.interface.imports import (
    LARGEST_FILE as LARGEST_FILE,
)
from waterfall.core.exchanges.interface.imports import (
    Confirmer as Confirmer,
)
from waterfall.core.exchanges.interface.imports import (
    DepositedFile as DepositedFile,
)
from waterfall.core.exchanges.interface.imports import (
    ExchangeKind as ExchangeKind,
)
from waterfall.core.exchanges.interface.imports import (
    Format as Format,
)
from waterfall.core.exchanges.interface.imports import (
    HeadToRead as HeadToRead,
)
from waterfall.core.exchanges.interface.imports import (
    ImportList as ImportList,
)
from waterfall.core.exchanges.interface.imports import (
    ImportMeans as ImportMeans,
)
from waterfall.core.exchanges.interface.imports import (
    ImportOpening as ImportOpening,
)
from waterfall.core.exchanges.interface.imports import (
    ImportRefused as ImportRefused,
)
from waterfall.core.exchanges.interface.imports import (
    ImportScope as ImportScope,
)
from waterfall.core.exchanges.interface.imports import (
    ImportTarget as ImportTarget,
)
from waterfall.core.exchanges.interface.imports import (
    ImportView as ImportView,
)
from waterfall.core.exchanges.interface.imports import (
    Judge as Judge,
)
from waterfall.core.exchanges.interface.imports import (
    abandon_import as abandon_import,
)
from waterfall.core.exchanges.interface.imports import (
    apply_import as apply_import,
)
from waterfall.core.exchanges.interface.imports import (
    deposit as deposit,
)
from waterfall.core.exchanges.interface.imports import (
    formats as formats,
)
from waterfall.core.exchanges.interface.imports import (
    head_to_read as head_to_read,
)
from waterfall.core.exchanges.interface.imports import (
    judge_deposit as judge_deposit,
)
from waterfall.core.exchanges.interface.imports import (
    list_imports as list_imports,
)
from waterfall.core.exchanges.interface.imports import (
    open_import as open_import,
)
from waterfall.core.exchanges.interface.imports import (
    read_import as read_import,
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

# ``loading`` (US-1650/L2): an import of the witness, written as it ended, without file nor task.
from waterfall.core.exchanges.interface.loading import (
    ImportLoad as ImportLoad,
)
from waterfall.core.exchanges.interface.loading import (
    load_import as load_import,
)

# ``purge`` (US-1380/L1; US-1420/L2): the purge of the exchanges, and what the storage loses.
from waterfall.core.exchanges.interface.purge import (
    Purged as Purged,
)
from waterfall.core.exchanges.interface.purge import (
    Stored as Stored,
)
from waterfall.core.exchanges.interface.purge import (
    purge as purge,
)
from waterfall.core.exchanges.interface.purge import (
    remove_purged as remove_purged,
)
from waterfall.core.exchanges.interface.purge import (
    stored_before as stored_before,
)

# ``xml`` (US-1380/L1): the hardened reader of an XML file deposited, for every XML format.
from waterfall.core.exchanges.interface.xml import (
    hardened_parser as hardened_parser,
)
