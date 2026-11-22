# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The examples of the contract of the exchanges that EP-33 changes (US-3250/L1, #4525).

The review of the 2026-11-14 found the exchanges' contract silent on five points; the author
decided each on the 2026-11-21 (`docs/api/DECISIONS.md`, « Le contrat des échanges d'EP-33 »), and
the contract precedes the service, each lot of the epic filling what it declares:

- ``import_apply_structure_changed.json``, the estimate of the amendment 2 analysed this morning
  (``import_analysed``), applied after an entry on that differential since its analysis
  (``estimate_line_updated_amendment``): refused for good by ``import_structure_unchanged``
  (WF-ARC-0100; US-3210, #4420);
- ``file_upload_permission_missing.json``, ``file_upload_pending_limit.json`` and
  ``file_upload_filename_nul.json``, a file uploaded by an account that holds none of the four
  import permissions, by one that already keeps twenty uploads unused, and under a name that
  holds the NUL character (WF-ADM-0020, WF-DAT-0120; US-3240, #4423, #4426);
- ``import_actual_costs_task_purged.json``, the extraction of April read today, applied on 4 May:
  the task of its application, ended more than thirty days ago, has been deleted with the result
  it kept, and the import reads its task null (WF-DAT-0080; US-3250, #4425);
- ``import_remaining_column_missing.json``, a remaining to commit whose tab of the control
  station has lost its column « Débours restant », renamed in the spreadsheet: refused at its
  opening, the column named with its tab (WF-INTF-0070; US-3200, #4421);
- ``import_remaining_amount_rounded.json``, a counterfactual variant of
  ``import_remaining_analysed``: the terminal blocks counted by the thousand, whose remaining
  amount the file carries at 1,234.56, which the import writes at 1,230.00, and signals
  (WF-INTF-0120; US-3230, #4428).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import mockcore, mocktext
from wftools.mockcorrelations import correlation
from wftools.mockexchanges import (
    APRIL_EXPIRES,
    APRIL_IMPORT,
    APRIL_SUBMITTED,
    april_report,
    import_commands,
    opened_on,
    tab_name,
)
from wftools.mockhistory import stamp
from wftools.mockwitness import SUBPROJECT_CONTROL, TODAY, N, fixture
from wftools.mockwitnesscosts import APRIL

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

type Entry = dict[str, Any]

STRUCTURE_CHANGED = "import_apply_structure_changed"
PERMISSION_MISSING = "file_upload_permission_missing"
PENDING_LIMIT = "file_upload_pending_limit"
FILENAME_NUL = "file_upload_filename_nul"
COLUMN_MISSING = "import_remaining_column_missing"
"""The names of the examples of a refusal, from which their correlation is derived (#1007)."""

IMPORT_PERMISSIONS = ("planning.write", "estimate.write", "remaining.write", "actual_costs.write")
"""The four permissions of an import, any of which opens the upload of a file; the refusal names
the first, as the writes of the grids name the first of theirs (#2601)."""

PENDING_UPLOADS = 20
"""The uploads for an import an account keeps unused at most (US-3240, decision of the author of
the 2026-11-21)."""

RETENTION = timedelta(
    days=fixture("system_status")["operating_parameters"]["background_task_retention_days"]
)
"""The retention of the result of a background task, at the end of which the task is deleted
(`OperatingParameters.background_task_retention_days`, §4.4.1)."""


# --- The application of an import whose structure was written since its analysis -------------


def import_apply_structure_changed() -> JsonObject:
    """Return what applyImport answers to an import whose structure was written since (#4420)."""
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "import_structure_unchanged"},
        "correlation_id": correlation(STRUCTURE_CHANGED),
    }


# --- The refusals of an upload (#4423, #4426) --------------------------------------------------


def file_upload_permission_missing() -> JsonObject:
    """Return what uploadFile answers to an account without any of the import permissions."""
    return {
        "code": "PERMISSION_MISSING",
        "status": 403,
        "params": {"missing_permission": IMPORT_PERMISSIONS[0]},
        "correlation_id": correlation(PERMISSION_MISSING),
    }


def file_upload_pending_limit() -> JsonObject:
    """Return what uploadFile answers to an account that keeps twenty uploads unused already."""
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "pending_uploads_below_limit", "maximum": PENDING_UPLOADS},
        "correlation_id": correlation(PENDING_LIMIT),
    }


def file_upload_filename_nul() -> JsonObject:
    """Return what uploadFile answers to a file whose name holds the NUL character."""
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/file", "code": "VALIDATION_FAILED"}],
        "correlation_id": correlation(FILENAME_NUL),
    }


# --- An import read once the task of its application is deleted (#4425) -----------------------


def applied_at() -> datetime:
    """Return when the extraction of April was applied, the instant its journal says."""
    return APRIL.event.instant


def import_actual_costs_task_purged() -> JsonObject:
    """Return what getImport answers today of the extraction of April, applied on 4 May.

    Its report is the one its analysis presented (``import_actual_costs_first``), which the
    application wrote as it was; the task of the application, ended more than the retention of
    its result ago, has been deleted: the import is read, its task null (WF-DAT-0080).
    """
    if TODAY - applied_at() <= RETENTION:
        message = "the application of April has not ended for longer than the retention"
        raise ValueError(message)
    report = april_report()
    status = "applied"
    return {
        "import_id": APRIL_IMPORT,
        "kind": "actual_costs",
        "filename": "couts-reels-2026-04.xlsx",
        **opened_on(None, APRIL.period),
        "status": status,
        "created_at": APRIL_SUBMITTED,
        "expires_at": APRIL_EXPIRES,
        "report": report,
        "task": None,
        "available_commands": import_commands(status, report),
    }


# --- A remaining to commit whose tab lost a column it reads (#4421) ----------------------------

REMAINING_VERSION = "1"
"""The version of the format of the remaining to commit (annex B)."""

LOST_HEADER = "Débours restant"
"""The column the tab of the control station lost: renamed « Débours restant (€) » in the
spreadsheet, a renamed header being a missing column."""


def import_remaining_column_missing() -> JsonObject:
    """Return what openImport answers to a remaining to commit whose tab lost a column it reads."""
    return {
        "code": "FILE_FORMAT_UNREADABLE",
        "status": 422,
        "params": {
            "expected_format": "remaining",
            "expected_version": REMAINING_VERSION,
            "missing_columns": [{"header": LOST_HEADER, "sheet": tab_name(SUBPROJECT_CONTROL)}],
        },
        "correlation_id": correlation(COLUMN_MISSING),
    }


# --- A remaining to commit whose amount is rounded by its unit disbursement (#4428) ------------

BLOCKS_QUANTITY = Decimal(1000)
"""The terminal blocks counted by the thousand, in the variant: a quantity the import keeps."""

TYPED_AMOUNT = Decimal("1234.56")
"""The remaining amount of the terminal blocks the file carries in « Débours restant »."""

COEFFICIENT = Decimal(1)
"""The inflation coefficient of the wiring of the cabinets: consumed in 2026, the reference year
of the current revision, the 102 (`revisions`)."""

CENT = Decimal("0.01")


def unit_disbursement(amount: Decimal) -> Decimal:
    """Give the unit disbursement the import writes: amount ÷ (quantity x coefficient), to the cent.

    Half away from zero, as every amount of the service is rounded (WF-DAT-0100).
    """
    return (amount / (BLOCKS_QUANTITY * COEFFICIENT)).quantize(CENT, rounding=ROUND_HALF_UP)


def written_amount(amount: Decimal) -> Decimal:
    """Give the amount the application writes: the unit disbursement x quantity x coefficient."""
    return (unit_disbursement(amount) * BLOCKS_QUANTITY * COEFFICIENT).quantize(CENT)


def import_remaining_amount_rounded() -> JsonObject:
    """Return import_remaining_analysed with the terminal blocks counted by the thousand.

    The file brings the remaining of the terminal blocks to 1,234.56 instead of setting their
    quantity to zero: the import writes their unit disbursement, the quantity kept, and the amount
    re-estimated is not the one the file carries; the report signals it (#4428).
    """
    analysed = cast("Entry", fixture("import_remaining_analysed"))
    report = cast("Entry", analysed["report"])
    blocks = mockcore.lineage(N.BLOCKS)
    differences: list[JsonValue] = [
        (
            {**difference, "fields": ["unit_disbursement"]}
            if difference["lineage_id"] == blocks
            else difference
        )
        for difference in cast("list[Entry]", report["differences"])
    ]
    [label] = [each["label"] for each in report["differences"] if each["lineage_id"] == blocks]
    signal: JsonObject = {
        "lineage_id": blocks,
        "label": label,
        "column": "unit_disbursement",
        "code": "AMOUNT_ROUNDED",
        "params": {
            "typed_amount": str(TYPED_AMOUNT),
            "written_amount": str(written_amount(TYPED_AMOUNT)),
        },
    }
    return {
        **analysed,
        "report": {**report, "differences": differences, "signals": [signal]},
    }


# --- The examples ------------------------------------------------------------------------------


def _purged_said() -> str:
    report = april_report()
    ended = applied_at()
    return (
        f"L'extraction d'avril (import_actual_costs_first), lue aujourd'hui : appliquée le "
        f"{mocktext.day(ended.date())} à {mocktext.hour(stamp(ended))} (cost_imports), son compte "
        f"rendu celui que son analyse présenta, {report['read_count']} lignes lues. La tâche de "
        f"son application, terminée depuis plus de {RETENTION.days} jours, la rétention de son "
        f"résultat (system_status), a été supprimée : l'import se lit toujours, sa tâche nulle, "
        f"et l'écran n'en suit aucune ; ni l'appliquer ni l'abandonner n'est offert "
        f"(WF-DAT-0080, WF-IHM-0090, #4425)."
    )


def examples() -> dict[str, JsonObject]:
    """Return the examples of the contract of the exchanges of EP-33, by file name."""
    analysed = cast("Entry", fixture("import_analysed"))
    rounded = import_remaining_amount_rounded()
    [signal] = cast("list[Entry]", cast("Entry", rounded["report"])["signals"])
    typed = Decimal(signal["params"]["typed_amount"])
    written = Decimal(signal["params"]["written_amount"])
    return {
        "import_apply_structure_changed.json": mocktext.example(
            f"L'application de « {analysed['filename']} » (import_analysed), le devis de "
            f"l'avenant 2 analysé ce matin, demandée après une saisie faite depuis sur ce "
            f"différentiel, la charge de l'« Assistance à la reprise des essais » passée de 40 à "
            f"48 h (estimate_line_updated_amendment) : le compte rendu ne dit plus ce que "
            f"l'application écrirait. Refusée pour de bon par la condition qui manque, une "
            f"structure inchangée depuis l'analyse ; l'import devient refusé (refused), son "
            f"fichier est supprimé, et l'utilisateur dépose de nouveau le fichier ; rien n'est "
            f"appliqué (WF-ARC-0100, #4420).",
            import_apply_structure_changed(),
        ),
        "file_upload_permission_missing.json": mocktext.example(
            "Un fichier déposé aujourd'hui pour un import par un compte qui ne porte aucune des "
            "quatre permissions d'import — un rôle de consultation seule : le dépôt est refusé, "
            f"la permission nommée la première des quatre, {IMPORT_PERMISSIONS[0]} ; rien n'est "
            "écrit au stockage objet ni dans la base (WF-ADM-0020, #4423).",
            file_upload_permission_missing(),
        ),
        "file_upload_pending_limit.json": mocktext.example(
            f"Un vingt et unième fichier déposé aujourd'hui pour un import par un compte qui en "
            f"garde déjà {PENDING_UPLOADS} qu'aucun import n'a employés et qui n'ont pas expiré : "
            f"refusé par la condition qui manque, le plafond nommé ; rien n'est écrit au stockage "
            f"objet. Dès qu'un import en emploie un, ou qu'un dépôt expire et est supprimé, un "
            f"nouveau dépôt passe (WF-DAT-0120, #4423).",
            file_upload_pending_limit(),
        ),
        "file_upload_filename_nul.json": mocktext.example(
            "Un fichier déposé aujourd'hui pour un import sous un nom qui porte le caractère NUL : "
            "refusé sur le fichier, comme tout texte qui le porte ; rien n'est écrit au stockage "
            "objet ni dans la base (#4426, #4423).",
            file_upload_filename_nul(),
        ),
        "import_actual_costs_task_purged.json": mocktext.example(
            _purged_said(), import_actual_costs_task_purged()
        ),
        "import_remaining_column_missing.json": mocktext.example(
            f"Un reste à engager déposé aujourd'hui dont l'onglet « "
            f"{tab_name(SUBPROJECT_CONTROL)} » a perdu sa colonne « {LOST_HEADER} », renommée "
            f"« {LOST_HEADER} (€) » dans le tableur : un en-tête renommé est une colonne absente. "
            f"Refusé à l'ouverture, le format et la version attendus nommés, et la colonne nommée "
            f"avec son onglet ; rien n'est analysé : aucun reste n'est mis à zéro, aucune tâche "
            f"n'est terminée (WF-INTF-0070, WF-INTF-0120, #4421).",
            import_remaining_column_missing(),
        ),
        "import_remaining_amount_rounded.json": mocktext.example(
            f"Variante contrefactuelle de import_remaining_analysed : les « {signal['label']} » "
            f"comptés par mille, une quantité de {mocktext.amount(BLOCKS_QUANTITY, 0)}, et le "
            f"fichier qui porte leur débours restant à {mocktext.amount(typed)}. L'import garde la "
            f"quantité et écrit le débours unitaire, arrondi au centime, le coefficient "
            f"d'inflation du « Câblage des armoires », consommé en 2026, année de référence de la "
            f"révision 102, valant 1 : le montant écrit est {mocktext.amount(written)}, que le "
            f"compte rendu signale avec le montant saisi ; une ligne dont le montant se divise "
            f"juste ne l'est pas (WF-INTF-0120, #4428).",
            rounded,
        ),
    }
