# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual costs of the witness and the journal of their imports, engendered (EP-02/L25).

The lines and the imports are described once (``mockwitness.COSTS``, ``mockwitness.JOURNAL``);
here they are read as the consultation of the costs and the journal present them today
(WF-CRE-0040, WF-CRE-0050), and as the indicators count them (``tracked``). What follows from the
description is computed, never written: the imputation of a line from its code of subproject
(WF-CRE-0020), its audit from the imports that brought it and its exclusion, the three totals,
the date of the last import, and the counts of lines each import created, updated and ignored.
And the answers of the exclusion of a line from the tracked scope and of its reinstatement, written
today (``setActualCostTrackedScope``, WF-CRE-0030), and the consultation read anew after the
exclusion. Nothing here reads the clock, nor a file the same command writes.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mocktext
from wftools.mockhistory import stamp
from wftools.mockstructure import money
from wftools.mockwitness import (
    APRIL,
    APRIL_AGAIN,
    COSTS,
    JOURNAL,
    MARCH,
    MAY,
    PASSTHROUGH,
    SUBPROJECT_CONTROL,
    TODAY,
    UNDATED,
    CostImport,
    CostLine,
    fixture,
    hex_identifier,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date, datetime

    from wftools.mockstructure import JsonObject, JsonValue

PAGE = 50
"""The page of the consultation and of the journal when none is asked (`Limit`)."""


def imputed(line: CostLine) -> str | None:
    """Return the subproject a line is imputed to: the one of its code, if the project has it.

    A line without a subproject part, or whose code no subproject of the project carries, is
    imputed to the project alone; the latter keeps its code (WF-CRE-0020).
    """
    known = {entry["code"]: entry["subproject_id"] for entry in fixture("subprojects")}
    return None if line.code is None else known.get(line.code)


def tracked() -> list[tuple[date, Decimal, str | None]]:
    """Return the lines of the tracked scope: their date of document, amount and subproject.

    A line excluded from the tracked scope enters no indicator (WF-CRE-0030).
    """
    return [(line.on, line.amount, imputed(line)) for line in COSTS if line.excluded is None]


def _actor() -> JsonObject:
    """Return the user who imports the costs of the witness: the one who created the project."""
    return cast("JsonObject", fixture("project")["audit"]["created_by"])


def _project() -> tuple[str, str]:
    project = fixture("project")
    return project["project_id"], project["code"]


def _passthrough(line: CostLine) -> dict[str, str]:
    """Return the columns of the file a line keeps, in the order the imports declare them."""
    _, code = _project()
    element = f"WF.{code}" if line.code is None else f"WF.{code}/{line.code}"
    values = dict(zip(PASSTHROUGH, (line.supplier, line.text, element), strict=True))
    return {column: values[column] for column in PASSTHROUGH}


def cost_line(line: CostLine) -> JsonObject:
    """Return a line as the consultation presents it (`ActualCostLine`)."""
    project_id, _ = _project()
    subproject = imputed(line)
    labels = {entry["subproject_id"]: entry["label"] for entry in fixture("subprojects")}
    created = line.imports[0].event.instant
    changes = [each.event.instant for each in line.imports]
    if line.excluded is not None:
        changes.append(line.excluded[0])
    actor = _actor()
    return {
        "cost_line_id": hex_identifier(line.number),
        "document_number": line.document,
        "document_date": line.on.isoformat(),
        "amount": money(line.amount),
        "project_id": project_id,
        "subproject_id": subproject,
        "subproject_code": line.code,
        "subproject_label": None if subproject is None else labels[subproject],
        "is_in_tracked_scope": line.excluded is None,
        "excluded_reason": None if line.excluded is None else line.excluded[1],
        "passthrough": cast("JsonObject", _passthrough(line)),
        "audit": {
            "created_at": stamp(created),
            "created_by": actor,
            "updated_at": stamp(max(changes)),
            "updated_by": actor,
        },
    }


EXCLUDED_TODAY = 0xC01
"""The line the exclusion written today takes out of the tracked scope: the cables of the desk."""

EXCLUSION_REASON = "Câbles d'un autre projet, à réimputer"
"""Why the line is excluded today, as the user wrote it."""


def _line(number: int) -> CostLine:
    [line] = [line for line in COSTS if line.number == number]
    return line


def _reinstated() -> CostLine:
    """Return the line the reinstatement written today brings back: the excluded one."""
    [line] = [line for line in COSTS if line.excluded is not None]
    return line


def written(line: CostLine, excluded: str | None) -> JsonObject:
    """Return a line as the write of its exclusion — or of its reinstatement — answers it today."""
    value = cost_line(replace(line, excluded=None if excluded is None else (TODAY, excluded)))
    audit = cast("JsonObject", value["audit"])
    audit["updated_at"] = stamp(TODAY)
    return value


def _excluded_today() -> list[CostLine]:
    """Return the lines of the witness once the exclusion written today has been applied."""
    return [
        replace(line, excluded=(TODAY, EXCLUSION_REASON)) if line.number == EXCLUDED_TODAY else line
        for line in COSTS
    ]


def last_import() -> datetime:
    """Return the instant of the last import of the journal (WF-CRE-0050).

    The date the consultation presents, whatever the filter: an import that brought no line
    of the project is an import still.
    """
    return max(entry.event.instant for entry in JOURNAL)


def passthrough_columns(lines: Sequence[CostLine]) -> list[str]:
    """Return the union of the columns kept of some lines, in the order the imports declared them.

    The imports in the order they were applied, the columns of an import in the order of its
    file, each column at its first declaration (``ActualCostListMeta``).
    """
    found: list[str] = []
    for entry in sorted(JOURNAL, key=lambda each: each.event.instant):
        for line in lines:
            if entry in line.imports:
                found.extend(column for column in _passthrough(line) if column not in found)
    return found


def consultation(lines: Sequence[CostLine], *, limit: int = PAGE, offset: int = 0) -> JsonObject:
    """Return the consultation of some lines: the most recent documents first, one page of them.

    The totals and the columns kept are those of every line retained, not of the page rendered
    (WF-CRE-0040, WF-CRE-0010); the last import is that of the journal, whatever the filter.
    """
    ordered = sorted(lines, key=lambda line: line.on, reverse=True)
    tracked_total = sum((line.amount for line in lines if line.excluded is None), Decimal(0))
    excluded_total = sum((line.amount for line in lines if line.excluded is not None), Decimal(0))
    return {
        "items": [cost_line(line) for line in ordered[offset : offset + limit]],
        "totals": {
            "tracked": money(tracked_total),
            "excluded": money(excluded_total),
            "overall": money(tracked_total + excluded_total),
        },
        "last_import_at": stamp(last_import()),
        "meta": {
            "limit": limit,
            "offset": offset,
            "total": len(lines),
            "passthrough_columns": cast("list[JsonValue]", passthrough_columns(lines)),
        },
    }


def counts(entry: CostImport) -> tuple[int, int, int]:
    """Return the lines an import created, updated and ignored (WF-CRE-0050).

    A line whose document number was already imported is updated, its exclusion kept; an unknown
    one is created (WF-CRE-0010); a line of another project is rejected, and ignored
    (WF-CRE-0020).
    """
    created = sum(1 for line in COSTS if line.imports[0] is entry)
    updated = sum(1 for line in COSTS if entry in line.imports[1:])
    return created, updated, entry.rejected


def journal_entry(entry: CostImport) -> JsonObject:
    """Return an import as the journal presents it (`CostImport`)."""
    created, updated, ignored = counts(entry)
    start, end = entry.period
    return {
        "cost_import_id": hex_identifier(entry.number),
        "imported_at": stamp(entry.event.instant),
        "actor": _actor(),
        "period_from": None if start is None else start.isoformat(),
        "period_to": None if end is None else end.isoformat(),
        "created_count": created,
        "updated_count": updated,
        "ignored_count": ignored,
    }


def journal() -> JsonObject:
    """Return the journal of the imports today, the most recent first."""
    entries = sorted(JOURNAL, key=lambda entry: entry.event.instant, reverse=True)
    return {
        "items": [journal_entry(entry) for entry in entries],
        "meta": {"limit": PAGE, "offset": 0, "total": len(entries)},
    }


def values() -> dict[str, JsonValue]:
    """Return the values of the examples of the costs, by name."""
    control = [line for line in COSTS if imputed(line) == SUBPROJECT_CONTROL]
    return {
        "actual_costs": consultation(COSTS),
        "actual_costs_page": consultation(COSTS, limit=1, offset=1),
        "actual_costs_subproject": consultation(control),
        "cost_imports": journal(),
        "actual_cost_excluded": written(_line(EXCLUDED_TODAY), EXCLUSION_REASON),
        "actual_cost_reinstated": written(_reinstated(), None),
        "actual_costs_after_exclusion": consultation(_excluded_today()),
    }


# --- What the summaries say ---------------------------------------------------------------------


def _amount(value: Decimal) -> str:
    return mocktext.amount(value)


def _lines(value: int) -> str:
    return "une ligne" if value == 1 else f"{mocktext.count(value)} lignes"


def _period(entry: CostImport) -> str:
    """Say the period an import extracted, from its bounds, each possibly missing."""
    start, end = entry.period
    if start is None and end is None:
        return "sans période"
    if start is None:
        return f"jusqu'au {mocktext.day(cast('date', end))}, sans début"
    if end is None:
        return f"à partir du {mocktext.day(start)}"
    return f"du {mocktext.day(start)} au {mocktext.day(end)}"


def _keeps_exclusion(entry: CostImport) -> bool:
    """Whether an import brings back a line excluded before it, whose exclusion it keeps."""
    return any(
        line.excluded is not None
        and entry in line.imports[1:]
        and line.excluded[0] < entry.event.instant
        for line in COSTS
    )


def _said(entry: CostImport) -> str:
    """Say what an import did, from its counts."""
    created, updated, ignored = counts(entry)
    parts: list[str] = []
    if created:
        parts.append(f"{_lines(created)} créée{'s' if created > 1 else ''}")
    if updated:
        parts.append(f"{_lines(updated)} mise{'s' if updated > 1 else ''} à jour")
    if ignored == 1:
        parts.append("une ligne d'un autre projet rejetée et signalée")
    elif ignored:
        parts.append(f"{_lines(ignored)} d'autres projets rejetées et signalées")
    return ", ".join(parts) if parts else "rien"


def _summaries(found: dict[str, JsonValue]) -> dict[str, str]:
    today = mocktext.day(TODAY.date())
    witness = cast("JsonObject", found["actual_costs"])
    totals = cast("JsonObject", witness["totals"])
    unknown = sorted({line.code for line in COSTS if line.code and imputed(line) is None})
    excluded = [line for line in COSTS if line.excluded is not None]
    [credit] = [line for line in COSTS if line.amount < 0]
    [screens] = [line for line in COSTS if imputed(line) == SUBPROJECT_CONTROL]
    [studies] = [line for line in COSTS if line.code is None]
    page = cast("list[JsonObject]", cast("JsonObject", found["actual_costs_page"])["items"])
    return {
        "actual_costs": (
            f"Les coûts réels du projet au {today}, après les {len(JOURNAL)} imports du journal, "
            f"les pièces les plus récentes d'abord : {len(COSTS) - len(excluded)} lignes suivies, "
            f"dont un avoir de {_amount(credit.amount)}, font les "
            f"{_amount(Decimal(cast('str', totals['tracked'])))} de coût réel des indicateurs ; "
            + ", ".join(f"« {line.text} », exclue du périmètre suivi," for line in excluded)
            + f" reste consultable. La facture des études de détail, {studies.document}, "
            f"{_amount(studies.amount)} datés du {mocktext.day(studies.on)}, jour où elles se "
            "terminent, n'a pas de partie sous-projet dans son OTP, comme leur ligne de devis : "
            "elle est imputée au seul projet. Les codes de sous-projet "
            + ", ".join(unknown)
            + ", lus dans l'OTP, ne sont ceux d'aucun sous-projet du projet : ces lignes sont "
            "imputées au seul projet, hors sous-projet, et présentées avec leur code ; "
            f"{screens.document}, sous {screens.code}, est imputée au sous-projet Poste de "
            "commande. Les colonnes conservées du fichier sont celles de toutes les lignes "
            "retenues (WF-CRE-0010, WF-CRE-0020, WF-CRE-0030, WF-CRE-0040, WF-CRE-0050)."
        ),
        "actual_costs_page": (
            "La même consultation lue une ligne par page (limit=1, offset=1) : la deuxième des "
            f"{len(COSTS)} lignes, {page[0]['document_number']}, et les totaux et les colonnes "
            "conservées de toutes les lignes retenues, pas de la seule page rendue (WF-CRE-0040)."
        ),
        "actual_costs_subproject": (
            "La consultation filtrée sur le sous-projet Poste de commande (subproject_id) au "
            f"{today} : la facture {screens.document} du {mocktext.day(screens.on)}, apportée par "
            f"l'import du {mocktext.day(screens.imports[0].event.on)}, imputée au sous-projet, "
            "nommé par son code "
            "et son libellé ; la date du dernier import reste celle du journal (WF-CRE-0020, "
            "WF-CRE-0040, WF-CRE-0050)."
        ),
        "actual_cost_excluded": (
            f"La facture {_line(EXCLUDED_TODAY).document}, « {_line(EXCLUDED_TODAY).text} », "
            f"exclue du périmètre suivi le {today} : « {EXCLUSION_REASON} ». Elle reste "
            "consultable et n'entre plus dans aucun indicateur (WF-CRE-0030, WF-CRE-0040)."
        ),
        "actual_costs_after_exclusion": (
            f"La consultation du {today} relue après l'exclusion de la facture "
            f"{_line(EXCLUDED_TODAY).document} : le périmètre suivi perd ses "
            f"{_amount(_line(EXCLUDED_TODAY).amount)}, que le total exclu gagne ; le total général "
            "ne change pas (WF-CRE-0030, WF-CRE-0040)."
        ),
        "actual_cost_reinstated": (
            f"La facture {_reinstated().document}, « {_reinstated().text} », exclue depuis le "
            f"{mocktext.day(cast('tuple[datetime, str]', _reinstated().excluded)[0].date())}, "
            f"réintégrée dans le périmètre suivi le {today} : elle entre de nouveau dans les "
            "indicateurs (WF-CRE-0030, WF-CRE-0040)."
        ),
        "cost_imports": (
            f"Le journal des imports de coûts réels au {today}, ses {len(JOURNAL)} imports du plus "
            "récent au plus ancien, dont trois n'ont pas déclaré toute leur période : celle de "
            f"mai, {_period(MAY)}, {_said(MAY)} ; une réextraction {_period(APRIL_AGAIN)}, "
            f"{_said(APRIL_AGAIN)}"
            + (", l'exclusion de la réception conservée" if _keeps_exclusion(APRIL_AGAIN) else "")
            + f" ; un fichier {_period(UNDATED)}, {_said(UNDATED)} ; puis l'extraction d'avril, "
            f"{_period(APRIL)}, {_said(APRIL)}, et celle de mars, {_period(MARCH)}, "
            f"{_said(MARCH)}. Le journal compte parmi les lignes ignorées celles "
            "qu'un import rejette (WF-CRE-0020, WF-CRE-0030, WF-CRE-0050)."
        ),
    }


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the actual costs of the witness, by file name."""
    found = values()
    summaries = _summaries(found)
    return {
        f"{name}.json": mocktext.example(summaries[name], value) for name, value in found.items()
    }
