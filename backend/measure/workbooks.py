# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``make measure-workbooks``: what a workbook deposited costs the readers, by vector (US-3190/L2b).

The measure the bounds of the workbooks were set on (EP-33, "Les bornes des classeurs"), kept so
that a bound can be measured again. It reads workbooks it engenders alone, never a file deposited:
the swollen ones of ``tests/workbook_bombs.py``, the exports of the writers and the extractions of
the tests' support, and the prototypes of the specification the tests read. Three commands, each
printing a JSON line by point:

- ``books``: the vectors of the workbooks engendered — strings, elements of a string, text, the
  lists of ``styles.xml``, the defined names, rows and cells of the tabs —, against which the
  margin of a bound is read;
- ``sweep <vector> <count>...``: the peak of the reading of a workbook swollen along one vector, by
  the reader of an estimate, each point in a fresh process — the peak resident size, and in another
  process the peak ``tracemalloc`` sees, which misses what libxml2 allocates;
- ``preread``: the time the judgment of the archive takes before openpyxl opens a workbook, on the
  export of 10 000 lines and the extraction of 18 000 lines: the opening by the opener, less the
  opening by openpyxl alone, the best of a few runs;
- ``members``: what the bounds of US-3190/L3 judge a workbook engendered on (#4914, #4915): the
  members openpyxl parses into a tree and the bytes each declares, and the nodes of its tabs and
  of its shared strings by where they lie, those openpyxl's stream never frees among them;
- ``peaks``: the peak resident size of a fresh process once it has imported the readers, once it
  has read the base workbook of a format, and what reading each workbook engendered adds.

The peaks of US-3190/L3 are those of the memory of the fresh process alone (``VmHWM``), beside the
rise ``ru_maxrss`` gives, which the tests read (``resident``): Linux keeps ``ru_maxrss`` across
``exec``, so a process spawned starts at the peak of the one that spawned it, and a read that rises
less than the gap is seen short, or not at all.

The vectors of US-3190/L3 swept: elements stuffed in a font of ``styles.xml`` — empty, by their
count; with a long attribute, a short text or a long text, by the mebibytes they inflate to —, the
``dxfs`` as Excel writes them by their count, and ``<x/>`` under the root of a tab read, in a cell
of it, or under the root of the shared strings, by their count. Each point gives the mebibytes the
members parsed into a tree declare, so that a peak is read against them.

It needs the tests' support on the path (the target sets it), runs no database, and never fails on
a figure: a figure is a report, and the chain does not run it.
"""

import argparse
import gc
import json
import multiprocessing
import posixpath
import resource
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from actual_costs_import_support import extraction, line
from estimate_import_support import workbook as estimate_workbook
from lxml import etree
from openpyxl import load_workbook
from remaining_import_support import workbook as remaining_workbook
from workbook_bombs import (
    READERS,
    STRINGS,
    STYLES,
    WORKBOOK,
    named,
    resident,
    shared_strings,
    shared_text,
    stuffed,
    styled,
    styled_richly,
    tab,
    tabulated,
)

from waterfall.core.estimate.excel.model import (
    Category,
    Estimate,
    Line,
    Lot,
    Nature,
    Role,
    Subproject,
    Tab,
    Task,
)
from waterfall.core.estimate.excel.writer import write_workbook
from waterfall.core.exchanges.interface import (
    MOST_CELLS,
    MOST_COLUMNS,
    MOST_NAMES,
    MOST_STRINGS,
    STYLE_LISTS,
    hardened_parser,
    opened_workbook,
)
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence, Sized

_PROTOTYPES = Path(__file__).resolve().parents[2] / "docs" / "spec" / "exemples"
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_SHEET = "1 Études"
_MEBIBYTE = 1024 * 1024


def _estimate(lines: int, tasks: int, tabs: int, entries: int) -> Estimate:
    """Give an estimate of ``lines`` lines in ``tasks`` tasks over ``tabs`` tabs.

    ``entries`` roles and categories, half each, and twenty subprojects: §4.6.2 at its ceiling.
    """
    half = entries // 2
    categories = tuple(
        Category(f"C{rank:03}", f"Catégorie {rank}", "Main-d’œuvre", Decimal(80 + rank % 40))
        for rank in range(half)
    )
    roles = tuple(
        Role(f"R{rank:03}", f"Rôle {rank}", f"Département {rank % 20}", f"C{rank:03}")
        for rank in range(half)
    )
    per_tab, per_task = tasks // tabs, lines // tasks
    built: list[Tab] = []
    for rank in range(tabs):
        held: list[Task] = []
        for task in range(per_tab):
            first = (rank * per_tab + task) * per_task
            held.append(
                Task(
                    lineage=f"t-{rank}-{task}",
                    number=f"{rank + 1}.{task + 1}",
                    label=f"Tâche {rank + 1}.{task + 1}",
                    start=date(2026, 11, 2),
                    end=date(2027, 3, 26),
                    description=f"Description de la tâche {rank + 1}.{task + 1}",
                    lines=tuple(
                        Line(
                            f"l-{number}",
                            role=f"R{number % half:03}",
                            category=None,
                            label=f"Ligne {number} — désignation",
                            quantity=Decimal(number % 9 + 1),
                            hours=Decimal("7.4"),
                            subproject=f"SP-{number % 20:02}",
                            amount=Decimal("100.00"),
                        )
                        for number in range(first, first + per_task)
                    ),
                )
            )
        built.append(Tab(f"{rank + 1}", f"Lot {rank + 1}", f"Lot {rank + 1}", tuple(held)))
    return Estimate(
        company="Exemple Industrie",
        client="Client Exemple",
        project="AFF-2026-014 Mesure des bornes",
        revision="Chiffrage v2 (en cours)",
        structure="Structure principale",
        reference_year=2026,
        currency="EUR",
        exported_at=datetime(2026, 11, 23, 8, tzinfo=UTC),
        natures=(Nature("Main-d’œuvre", "labour"),),
        categories=categories,
        roles=roles,
        subprojects=tuple(Subproject(f"SP-{rank:02}", f"Sous-projet {rank}") for rank in range(20)),
        lots=(Lot("1", "Lot", tuple(built)),),
    )


def _extraction(lines: int) -> bytes:
    """Give an extraction of ``lines`` lines of cost, as the tests' support writes one."""
    return extraction(
        [
            line(number=f"51{rank:08}", supplier=f"Fournisseur {rank % 500}", matricule=f"M{rank}")
            for rank in range(lines)
        ]
    )


EXPORT = "estimate-export-10000-lines"
EXTRACTION = "extraction-18000-lines"
BOOKS: dict[str, Callable[[], bytes]] = {
    "estimate-prototype": (_PROTOTYPES / "devis-prototype.xlsx").read_bytes,
    "remaining-prototype": (_PROTOTYPES / "rae-prototype.xlsx").read_bytes,
    "estimate-export-10-lines": lambda: write_workbook(_estimate(10, 5, 2, 4)),
    "remaining-of-the-tests": lambda: remaining_workbook({"Hors sous-projet": []}),
    EXPORT: lambda: write_workbook(_estimate(10_000, 1_000, 20, 350)),
    EXTRACTION: lambda: _extraction(18_000),
}


def _base() -> bytes:
    return estimate_workbook([])


def _styled(listing: str, count: int) -> bytes:
    return styled(_base(), listing, count)


def _combined(_: int) -> bytes:
    """Give the workbook of every vector at its bound at once, its text apart."""
    content = shared_strings(_base(), MOST_STRINGS)
    for listing, most in STYLE_LISTS.items():
        content = styled(content, listing, most)
    content = named(content, MOST_NAMES, _SHEET)
    return tabulated(content, tab(content, _SHEET), MOST_CELLS // MOST_COLUMNS, MOST_COLUMNS)


# The elements of #4914, stuffed in a font of ``styles.xml``: with an attribute of 190 characters,
# a text of as many, or a text of 8 KiB; and the element of #4915, out of any row, cell or string.
_ATTRIBUTE = b'<b a="' + b"a" * 190 + b'"/>'
_TEXT = b"<b>" + b"a" * 190 + b"</b>"
_LONG_TEXT = b"<b>" + b"a" * (8 * 1024 - 7) + b"</b>"
_FOREIGN = b"<x/>"
# The first tab of the base, which the reader of an estimate reads: its header.
_READ_TAB = "xl/worksheets/sheet1.xml"


def _in_a_font(element: bytes, mebibytes: int) -> bytes:
    """Give the base whose font holds as many ``element`` as inflate to ``mebibytes`` MiB."""
    return stuffed(_base(), STYLES, b"</font>", element, mebibytes * _MEBIBYTE // len(element))


def _foreign_strings(count: int) -> bytes:
    """Give the base of one shared string, ``count`` elements ``<x/>`` under the root more."""
    return stuffed(shared_strings(_base(), 1), STRINGS, b"</sst>", _FOREIGN, count)


VECTORS: dict[str, Callable[[int], bytes]] = {
    "strings": lambda count: shared_strings(_base(), count),
    "string-elements": lambda count: shared_strings(_base(), 1, count),
    "text": lambda count: shared_text(_base(), count, astral=True),
    "names": lambda count: named(_base(), count, _SHEET),
    **{f"styles-{listing}": partial(_styled, listing) for listing in STYLE_LISTS},
    "rows": lambda count: tabulated(_base(), tab(_base(), _SHEET), count, 1),
    "cells-500-columns": lambda count: tabulated(
        _base(), tab(_base(), _SHEET), max(1, count // 500), 500
    ),
    "combined": _combined,
    "font-empty-b": lambda count: stuffed(_base(), STYLES, b"</font>", b"<b/>", count),
    "font-attribute-mib": partial(_in_a_font, _ATTRIBUTE),
    "font-text-mib": partial(_in_a_font, _TEXT),
    "font-long-text-mib": partial(_in_a_font, _LONG_TEXT),
    "dxfs-rich": lambda count: styled_richly(_base(), count),
    "foreign-under-a-tab": lambda count: stuffed(
        _base(), _READ_TAB, b"</worksheet>", _FOREIGN, count
    ),
    "foreign-in-a-cell": lambda count: stuffed(_base(), _READ_TAB, b"</c>", _FOREIGN, count),
    "foreign-under-the-strings": _foreign_strings,
}

# What openpyxl parses into a tree by a fixed name: all of them but the theme, which it keeps as
# bytes; and the relations of the workbook, which name the parts whose relations it parses too.
_FIXED_TREES = (
    "[Content_Types].xml",
    "docProps/core.xml",
    "docProps/custom.xml",
    STYLES,
    WORKBOOK,
)
_WORKBOOK_RELATIONS = "xl/_rels/workbook.xml.rels"
_TABS = "xl/worksheets/"


def trees(content: bytes) -> dict[str, int]:
    """Give the members openpyxl parses into a tree, and the bytes each declares.

    As the opener finds them for a workbook of no chartsheet and no external link, the workbooks
    measured here: the fixed names but the theme, the relations of the workbook, and those of each
    part it names. Two members of one name add up.
    """
    with zipfile.ZipFile(BytesIO(content)) as archive:
        sizes: dict[str, int] = {}
        for item in archive.infolist():
            sizes[item.filename] = sizes.get(item.filename, 0) + item.file_size
        named = {_WORKBOOK_RELATIONS}
        if _WORKBOOK_RELATIONS in sizes:
            relations = etree.fromstring(archive.read(_WORKBOOK_RELATIONS), hardened_parser())
            for relation in relations:
                target = relation.get("Target")
                if target is None or relation.get("TargetMode") == "External":
                    continue
                part = target[1:] if target.startswith("/") else posixpath.join("xl", target)
                folder, name = posixpath.split(posixpath.normpath(part))
                named.add(posixpath.join(folder, "_rels", f"{name}.rels"))
    return {name: sizes[name] for name in (*_FIXED_TREES, *sorted(named)) if name in sizes}


def _local(tag: object) -> str:
    """Give the local name of a tag; a comment or an instruction by ``#node``."""
    return tag.rpartition("}")[2] if isinstance(tag, str) else "#node"


def _add(found: dict[str, int], key: str, count: int = 1) -> None:
    found[key] = found.get(key, 0) + count


def placed(data: bytes) -> dict[str, int]:
    """Give the nodes of a tab or of the shared strings by where they lie.

    ``row`` and ``c``, a row of ``sheetData`` and its cells, ``row/<tag>`` another child of a row,
    ``c/<tag>`` what a cell holds, at any depth; ``si`` a string, ``si/<tag>`` what it holds; any
    other child of the root by its local name, and ``<tag>/<tag>`` what it holds, at any depth.
    """
    found: dict[str, int] = {}
    for child in etree.fromstring(data, hardened_parser()):
        name = _local(child.tag)
        if name != "sheetData":
            _add(found, name)
            for node in child.iterdescendants():
                _add(found, f"{name}/{_local(node.tag)}")
            continue
        for row in child:
            _add(found, "row")
            for cell in row:
                key = "c" if _local(cell.tag) == "c" else f"row/{_local(cell.tag)}"
                _add(found, key)
                for node in cell.iterdescendants():
                    _add(found, f"{key}/{_local(node.tag)}")
    return dict(sorted(found.items()))


def _members(_: argparse.Namespace) -> None:
    for name, book in BOOKS.items():
        content = book()
        held = trees(content)
        point: dict[str, object] = {"book": name, "tree_bytes": sum(held.values()), "trees": held}
        with zipfile.ZipFile(BytesIO(content)) as archive:
            tabs: dict[str, int] = {}
            for member in archive.namelist():
                if member.startswith(_TABS) and member.endswith(".xml"):
                    for key, count in placed(archive.read(member)).items():
                        _add(tabs, key, count)
            point["tabs"] = dict(sorted(tabs.items()))
            if STRINGS in archive.namelist():
                point["strings"] = placed(archive.read(STRINGS))
        _write(point)


def _children(element: Sized | None) -> int:
    return 0 if element is None else len(element)


def vectors(content: bytes) -> dict[str, int]:
    """Give the vectors of a workbook: what each bound is judged on, and its size."""
    found: dict[str, int] = {"bytes": len(content)}
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = set(archive.namelist())
        found["inflated"] = sum(item.file_size for item in archive.infolist())
        strings = elements = text = 0
        if STRINGS in names:
            table = etree.fromstring(archive.read(STRINGS), hardened_parser())
            for string in table.iter(f"{_MAIN}si"):
                strings += 1
                elements = max(elements, sum(1 for _ in string.iter()) - 1)
                text += sum(len(piece) for piece in string.itertext())
        found.update(strings=strings, most_elements_of_a_string=elements, text=text)
        styles = etree.fromstring(archive.read(STYLES), hardened_parser())
        for listing in STYLE_LISTS:
            held = styles.find(f"{_MAIN}{listing}")
            found[listing] = (
                sum(1 for _ in held.iter()) - 1
                if listing == "colors" and held is not None
                else _children(held)
            )
        book = etree.fromstring(archive.read(WORKBOOK), hardened_parser())
        found["names"] = len(book.findall(f".//{_MAIN}definedName"))
    with opened_workbook(content) as opened:
        rows = cells = 0
        for sheet in opened.worksheets:
            for row in sheet.iter_rows(values_only=True):
                rows += 1
                cells += len(row)
        found.update(rows=rows, cells=cells)
    return found


def _write(point: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(point, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _books(_: argparse.Namespace) -> None:
    for name, book in BOOKS.items():
        _write({"book": name, **vectors(book())})


def _high_water() -> int:
    """Give the peak resident size of the memory of this process alone, in bytes (``VmHWM``).

    ``ru_maxrss`` is no measure of a process spawned: Linux keeps it across ``exec``, so that it
    starts at the peak of the process that spawned it, and a read that rises less than the gap is
    not seen at all. ``VmHWM`` is that of the memory of the process, which ``exec`` makes anew.
    """
    for entry in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
        if entry.startswith("VmHWM:"):
            return int(entry.split()[1]) * 1024
    return 0


def _maxrss() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def _read_fresh(reader: str, base: bytes, content: bytes) -> dict[str, object]:
    """Read ``base`` to warm ``reader``, then ``content``: the peaks, in the process spawned."""
    gc.collect()
    imported = _high_water()
    READERS[reader](base)
    gc.collect()
    warmed, before = _high_water(), _maxrss()
    start = time.perf_counter()
    outcome = "read"
    try:
        READERS[reader](content)
    except UnprocessableError as error:
        outcome = error.code
    seconds = time.perf_counter() - start
    peak = _high_water()
    return {
        "outcome": outcome,
        "imported_mib": round(imported / _MEBIBYTE, 1),
        "warmed_mib": round(warmed / _MEBIBYTE, 1),
        "peak_mib": round(peak / _MEBIBYTE, 1),
        "rise_mib": round((peak - warmed) / _MEBIBYTE, 1),
        "maxrss_rise_mib": round((_maxrss() - before) / _MEBIBYTE, 1),
        "seconds": round(seconds, 3),
    }


def fresh(reader: str, base: bytes, content: bytes) -> dict[str, object]:
    """Read ``content`` by ``reader`` in a fresh process, warmed on ``base``: what it gave.

    The outcome, ``read`` or the code of the refusal; ``imported_mib``, ``warmed_mib`` and
    ``peak_mib``, the peak of the memory of the process once the readers are imported, once
    ``base`` is read, once ``content`` is; ``rise_mib`` what the read of ``content`` added; and
    ``maxrss_rise_mib``, the rise ``resident`` of the tests sees, by ``ru_maxrss``.
    """
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        return pool.submit(_read_fresh, reader, base, content).result()


def _sweep(arguments: argparse.Namespace) -> None:
    base = _base()
    for count in arguments.counts:
        content = VECTORS[arguments.vector](count)
        point: dict[str, object] = {
            "vector": arguments.vector,
            "count": count,
            "bytes": len(content),
            "tree_mib": round(sum(trees(content).values()) / _MEBIBYTE, 2),
        }
        point.update(fresh("estimate", base, content))
        if not arguments.resident_only:
            (traced,) = resident("estimate", base, [content], traced=True)
            point["traced_mib"] = round((traced.traced or 0) / _MEBIBYTE, 1)
        _write(point)


# The reader of each workbook engendered, and the base of its format it is warmed on.
_READ_BY: dict[str, str] = {
    "estimate-prototype": "estimate",
    "remaining-prototype": "remaining",
    "estimate-export-10-lines": "estimate",
    "remaining-of-the-tests": "remaining",
    EXPORT: "estimate",
    EXTRACTION: "actual_costs",
}
_BASES: dict[str, Callable[[], bytes]] = {
    "estimate": _base,
    "remaining": BOOKS["remaining-of-the-tests"],
    "actual_costs": lambda: _extraction(1),
}


def _peaks(_: argparse.Namespace) -> None:
    for name, reader in _READ_BY.items():
        _write({"book": name, "reader": reader, **fresh(reader, _BASES[reader](), BOOKS[name]())})


def _best(call: Callable[[], object], runs: int) -> float:
    durations: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        call()
        durations.append(time.perf_counter() - start)
    return min(durations)


def _opened(content: bytes) -> None:
    with opened_workbook(content):
        pass


def _loaded(content: bytes) -> None:
    load_workbook(BytesIO(content), read_only=True, data_only=True).close()


def _preread(arguments: argparse.Namespace) -> None:
    for name, reader in ((EXPORT, "estimate"), (EXTRACTION, "actual_costs")):
        content = BOOKS[name]()
        opened = _best(lambda content=content: _opened(content), arguments.runs)
        loaded = _best(lambda content=content: _loaded(content), arguments.runs)
        read = _best(lambda content=content, reader=reader: READERS[reader](content), 1)
        _write(
            {
                "book": name,
                "bytes": len(content),
                "opened_ms": round(opened * 1000, 1),
                "loaded_ms": round(loaded * 1000, 1),
                "judged_ms": round((opened - loaded) * 1000, 1),
                "read_ms": round(read * 1000, 1),
            }
        )


def main(argv: Sequence[str] | None = None) -> None:
    """Run the command asked; print a JSON line by point."""
    parser = argparse.ArgumentParser(prog="python -m measure.workbooks", description=__doc__)
    commands = parser.add_subparsers(required=True)
    commands.add_parser("books", help="the vectors of the workbooks engendered").set_defaults(
        run=_books
    )
    sweep = commands.add_parser("sweep", help="the peak of a reading, along one vector")
    sweep.add_argument("vector", choices=list(VECTORS))
    sweep.add_argument("counts", type=int, nargs="+")
    sweep.add_argument(
        "--resident-only", action="store_true", help="leave the peak tracemalloc sees"
    )
    sweep.set_defaults(run=_sweep)
    preread = commands.add_parser("preread", help="the time the judgment of the archive takes")
    preread.add_argument("--runs", type=int, default=5)
    preread.set_defaults(run=_preread)
    commands.add_parser(
        "members", help="the members parsed into a tree, and where the nodes of the tabs lie"
    ).set_defaults(run=_members)
    commands.add_parser(
        "peaks", help="the peak of a fresh process, and what each workbook engendered adds"
    ).set_defaults(run=_peaks)
    arguments = parser.parse_args(argv)
    arguments.run(arguments)


if __name__ == "__main__":
    main()
