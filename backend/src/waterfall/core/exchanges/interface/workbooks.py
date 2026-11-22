# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The opener of a workbook a user deposited: the only one every reader of a workbook employs.

A workbook is a zip, whose members openpyxl inflates whole — its theme, its styles, its shared
strings — before a single row is read: ten mebibytes deposited may hold gigabytes once inflated
(#4419). So the opener judges the archive before openpyxl sees it (US-3190; EP-33, "Les bornes
des classeurs"): first its directory, ``infolist()``, without inflating anything — more than
``MOST_MEMBERS`` members, or more than ``LARGEST_INFLATED`` bytes of sizes declared, is refused —,
then each member the size it declares. zipfile cuts a member at its declared size, but only once it
has inflated it: ``ZipFile.read`` inflates a member whole in one call, so a member that declares
7 000 bytes and inflates to 64 MiB holds 64 MiB before the cut — and passes, when its CRC is that
of its first 7 000 bytes. The opener inflates each member by bounded steps, never more than one
byte past what it declares, and refuses one that holds more; a member neither stored nor deflated,
whose inflation zipfile does not bound, or encrypted, is refused too (Excel writes none). Only then
is the workbook opened, read-only and by values.

The cost, accepted: the check inflates each deflated member once more than openpyxl will, and it is
replayed at each judgment of a file (the header, the analysis, the application), so a workbook at
the bound, 200 MiB declared, inflates up to 200 MiB per judgment, for some hundreds of
milliseconds, a step of a mebibyte at a time and never held. A workbook of the format weighs
a few mebibytes inflated; the bound is a worst case, which a user may reach only by depositing
a file that is refused anyway, and no bound could be had without inflating.

A reader then materialises the tabs its format reads, and those alone, by ``bounded_rows``: a tab
of more than ``MOST_ROWS`` rows or ``MOST_COLUMNS`` columns, as openpyxl gives them, is refused.

Every refusal raises ``WorkbookOutOfBoundsError``, which ``DAMAGES`` lists: each reader turns it
into the refusal of its format, ``FILE_FORMAT_UNREADABLE``, as it does a damaged file.
"""

import zipfile
import zlib
from contextlib import contextmanager
from io import BytesIO
from typing import TYPE_CHECKING, Any

from openpyxl import load_workbook

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from openpyxl.workbook.workbook import Workbook

# The bounds of the design (EP-33, "Les bornes des classeurs"): 200 MiB declared, twenty times the
# largest file deposited; 200 000 rows, ten times the 18 000 lines of cost of §4.6.2; 500 columns,
# for the columns kept of an extraction.
LARGEST_INFLATED = 200 * 1024 * 1024
MOST_MEMBERS = 1_000
MOST_ROWS = 200_000
MOST_COLUMNS = 500

# The steps of the inflation of a member: what is fed, and the most that one step gives.
_FED = 64 * 1024
_STEP = 1024 * 1024
# The local header of a member (APPNOTE 4.3.7): its signature, its fixed length, and where the
# lengths of its name and of its extra field are.
_LOCAL_SIGNATURE = b"PK\x03\x04"
_LOCAL_LENGTH = 30
_NAME_LENGTH_AT = 26
_EXTRA_LENGTH_AT = 28
_ENCRYPTED = 0x1


class WorkbookOutOfBoundsError(ValueError):
    """A workbook, or a tab of it, beyond a bound: refused as a damaged workbook is."""


def _judge_directory(members: list[zipfile.ZipInfo]) -> None:
    """Refuse a directory of too many members, or whose declared sizes add up beyond the bound."""
    if len(members) > MOST_MEMBERS:
        msg = f"{len(members)} members, more than {MOST_MEMBERS}"
        raise WorkbookOutOfBoundsError(msg)
    declared = sum(member.file_size for member in members)
    if declared > LARGEST_INFLATED:
        msg = f"{declared} bytes declared, more than {LARGEST_INFLATED}"
        raise WorkbookOutOfBoundsError(msg)


def _stream_of(content: bytes, member: zipfile.ZipInfo) -> memoryview:
    """Give the compressed bytes of a member, after its local header (APPNOTE 4.3.7)."""
    at = member.header_offset
    if content[at : at + len(_LOCAL_SIGNATURE)] != _LOCAL_SIGNATURE:
        msg = f"no local header for {member.filename!r}"
        raise zipfile.BadZipFile(msg)
    name = int.from_bytes(content[at + _NAME_LENGTH_AT : at + _NAME_LENGTH_AT + 2], "little")
    extra = int.from_bytes(content[at + _EXTRA_LENGTH_AT : at + _EXTRA_LENGTH_AT + 2], "little")
    start = at + _LOCAL_LENGTH + name + extra
    return memoryview(content)[start : start + member.compress_size]


def _judge_inflation(content: bytes, member: zipfile.ZipInfo) -> None:
    """Refuse a member that inflates to more than it declares, holding a step at most at a time."""
    if member.flag_bits & _ENCRYPTED:
        msg = f"{member.filename!r} is encrypted"
        raise WorkbookOutOfBoundsError(msg)
    if member.compress_type == zipfile.ZIP_STORED:
        # A stored member is read as it lies in the file: never more than the file holds.
        return
    if member.compress_type != zipfile.ZIP_DEFLATED:
        msg = f"{member.filename!r} is compressed by method {member.compress_type}"
        raise WorkbookOutOfBoundsError(msg)
    stream = _stream_of(content, member)
    inflater = zlib.decompressobj(-zlib.MAX_WBITS)
    allowed = member.file_size + 1
    inflated = 0
    for start in range(0, len(stream), _FED):
        pending: bytes | memoryview = stream[start : start + _FED]
        while pending and not inflater.eof:
            inflated += len(inflater.decompress(pending, min(_STEP, allowed - inflated)))
            if inflated > member.file_size:
                break
            pending = inflater.unconsumed_tail
        if inflated > member.file_size or inflater.eof:
            break
    # What a step left inflated with no input to feed: the end of the last match.
    while inflated <= member.file_size and not inflater.eof:
        given = len(inflater.decompress(b"", min(_STEP, allowed - inflated)))
        if not given:
            break
        inflated += given
    if inflated > member.file_size:
        msg = f"{member.filename!r} inflates beyond the {member.file_size} bytes it declares"
        raise WorkbookOutOfBoundsError(msg)


def _judge_archive(content: bytes) -> None:
    """Refuse a workbook whose archive is beyond the bounds, before openpyxl reads any of it.

    Raises ``WorkbookOutOfBoundsError`` for the bounds, ``zipfile.BadZipFile`` or ``zlib.error``
    for a file that is no zip or whose member is damaged: all of them in ``DAMAGES``.
    """
    with zipfile.ZipFile(BytesIO(content)) as archive:
        members = archive.infolist()
    _judge_directory(members)
    for member in members:
        _judge_inflation(content, member)


@contextmanager
def opened_workbook(content: bytes) -> Generator[Workbook]:
    """Open a workbook deposited, read-only and by values, once its archive is judged; close it.

    Whatever the judgment or openpyxl raises is the caller's to turn into its refusal, by
    ``DAMAGES``: in read-only mode the XML of a tab is parsed while iterating, so the reading of the
    rows belongs inside the ``with``.
    """
    _judge_archive(content)
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        yield workbook
    finally:
        workbook.close()


def bounded_rows(rows: Iterable[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    """Materialise the rows of a tab, refused past ``MOST_ROWS`` rows or ``MOST_COLUMNS`` columns.

    The rows are those openpyxl gives (``iter_rows(values_only=True)``), each as wide as the tab
    says it is: a row past a bound is refused as it comes, before the next is read.
    """
    kept: list[tuple[Any, ...]] = []
    for row in rows:
        if len(kept) == MOST_ROWS:
            msg = f"a tab of more than {MOST_ROWS} rows"
            raise WorkbookOutOfBoundsError(msg)
        if len(row) > MOST_COLUMNS:
            msg = f"a tab of more than {MOST_COLUMNS} columns"
            raise WorkbookOutOfBoundsError(msg)
        kept.append(row)
    return kept
