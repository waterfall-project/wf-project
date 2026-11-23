# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a damaged workbook raises as openpyxl opens or reads it: the only list every reader uses.

The reader of an estimate and the reader of the actual costs each turn these exceptions into the
refusal of their format; a list of their own would drift from the other's (#2723). SyntaxError is
the parent of ``ElementTree.ParseError`` and of lxml's ``XMLSyntaxError``; ``zlib.error`` and
``EOFError`` are a cut deflate stream, ``RuntimeError`` and ``NotImplementedError`` a member that
zipfile cannot decode (encrypted, unknown compression): none of them is an ``OSError``.
``WorkbookOutOfBoundsError`` is a workbook the opener refuses before openpyxl reads it, or a tab
past the bounds (``workbooks``, US-3190): refused as a damaged one. ``WorkbookDamagedError``, a
``ValueError``, is a ``TypeError`` openpyxl raised at the opening or at the reading of the rows,
which the opener alone turns so (#4848): ``TypeError`` itself is not listed, so that an error of a
reader's own code is not taken for a damaged file.
"""

import zipfile
import zlib

from openpyxl.utils.exceptions import InvalidFileException

from waterfall.core.exchanges.interface.workbooks import WorkbookOutOfBoundsError

DAMAGES: tuple[type[Exception], ...] = (
    WorkbookOutOfBoundsError,
    zipfile.BadZipFile,
    zlib.error,
    EOFError,
    RuntimeError,
    NotImplementedError,
    InvalidFileException,
    KeyError,
    ValueError,
    OSError,
    SyntaxError,
)
