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
  opening by openpyxl alone, the best of a few runs.

It needs the tests' support on the path (the target sets it), runs no database, and never fails on
a figure: a figure is a report, and the chain does not run it.
"""

import argparse
import json
import sys
import time
import zipfile
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
    STYLE_LISTS,
    STYLES,
    WORKBOOK,
    named,
    resident,
    shared_strings,
    shared_text,
    styled,
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
from waterfall.core.exchanges.interface import hardened_parser, opened_workbook

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence, Sized

_PROTOTYPES = Path(__file__).resolve().parents[2] / "docs" / "spec" / "exemples"
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_SHEET = "1 Études"
_MEBIBYTE = 1024 * 1024
# The bounds the author set on 2026-11-23, each vector at its bound in one workbook (``combined``).
_AT_BOUNDS = {
    "numFmts": 1_000,
    "fonts": 1_024,
    "fills": 1_024,
    "borders": 1_024,
    "cellStyleXfs": 65_490,
    "cellXfs": 65_490,
    "cellStyles": 65_490,
    "dxfs": 65_490,
    "tableStyles": 1_024,
    "colors": 1_024,
}


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
    content = shared_strings(_base(), 1_000_000)
    for listing, most in _AT_BOUNDS.items():
        content = styled(content, listing, most)
    content = named(content, 10_000, _SHEET)
    return tabulated(content, tab(content, _SHEET), 20_000, 500)


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
}


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
    with opened_workbook(content) as workbook:
        rows = cells = 0
        for sheet in workbook.worksheets:
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


def _sweep(arguments: argparse.Namespace) -> None:
    base = _base()
    for count in arguments.counts:
        content = VECTORS[arguments.vector](count)
        point: dict[str, object] = {
            "vector": arguments.vector,
            "count": count,
            "bytes": len(content),
        }
        (rss,) = resident("estimate", base, [content])
        (traced,) = resident("estimate", base, [content], traced=True)
        point.update(
            outcome=rss.outcome,
            rss_mib=round(rss.rise / _MEBIBYTE, 1),
            traced_mib=round((traced.traced or 0) / _MEBIBYTE, 1),
            seconds=round(rss.seconds, 3),
        )
        _write(point)


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
    sweep.set_defaults(run=_sweep)
    preread = commands.add_parser("preread", help="the time the judgment of the archive takes")
    preread.add_argument("--runs", type=int, default=5)
    preread.set_defaults(run=_preread)
    arguments = parser.parse_args(argv)
    arguments.run(arguments)


if __name__ == "__main__":
    main()
