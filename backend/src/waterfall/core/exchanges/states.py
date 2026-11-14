# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Where an import stands as it is read, and its commands, private to the module (EP-06).

The state an import is read in is judged at the reading, from what its row keeps, what its last
task became and the instant of the reading: an ``analysed`` import whose report expired reads
``expired`` until the purge writes it (US-1420/L2), and an import whose analysis or application
failed without leaving its trace — the attempts of its task spent by a worker stopped each time —
reads ``failed``. One judgment serves the reading, the commands it lists and the refusals of
``applyImport`` and ``abandonImport``, so that a command said unavailable and the call refused
name the same condition (WF-IHM-0090; I-01, I-02, #1789).
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

# The conditions the commands of an import lack (``CommandCondition``).
AWAITING_DECISION = "import_awaiting_decision"
CALENDAR_GAP = "import_calendar_gap"
FILE_ACCEPTED = "import_file_accepted"
NOT_APPLIED = "import_not_applied"
IS_CONTRIBUTOR = "is_contributor"
# The states of an import whose task runs; those in which it has written or writes.
RUNNING = ("analysing", "applying")
WRITING = ("applying", "applied")
# The states in which an import keeps its file: it is being analysed, awaits its decision, or is
# being applied.
FILE_KEPT = ("analysing", "analysed", "applying")
# The states of an import that ended without writing: abandoning it again changes nothing.
ENDED_WITHOUT_WRITING = ("abandoned", "expired", "failed", "refused")


def status_read(
    status: str, expires_at: datetime | None, now: datetime, *, task_failed: bool
) -> str:
    """Give the state an import is read in at ``now``: its expiry and the end of its task judged."""
    if status == "analysed" and expires_at is not None and expires_at <= now:
        return "expired"
    if status in RUNNING and task_failed:
        return "failed"
    return status


def expiry_read(read: str, expires_at: datetime | None) -> datetime | None:
    """Give the instant an import's report expires at, as it is read: none once it failed."""
    return None if read in {"failed", "refused"} else expires_at


def rejects_the_file(report: Mapping[str, Any] | None) -> bool:
    """Tell whether a report rejects the whole file (``ImportReport.refusals``, EP-14/L42s)."""
    return bool(report and report.get("refusals"))


def rule_of(report: Mapping[str, Any] | None) -> str | None:
    """Give the rule of the durations a report was computed under; ``None`` without a calendar gap.

    A report of another kind, or analysed before the gap was (#2977), carries none (US-2000).
    """
    gap = None if report is None else report.get("calendar_gap")
    return None if not gap else gap["duration_rule"]


def rule_lacks(read: str, report: Mapping[str, Any] | None) -> tuple[str, ...]:
    """Name what a change of the rule of the durations lacks, in the order of the contract.

    An import that no longer awaits its decision first, as for its application; then a report
    without a calendar gap, which offers no choice (``setImportDurationRule``).
    """
    if read != "analysed":
        return (AWAITING_DECISION,)
    if rule_of(report) is None:
        return (CALENDAR_GAP,)
    return ()


def apply_lacks(read: str, report: Mapping[str, Any] | None) -> tuple[str, ...]:
    """Name what the application of an import lacks, in the order of the contract (I-01)."""
    if read != "analysed":
        return (AWAITING_DECISION,)
    if rejects_the_file(report):
        return (FILE_ACCEPTED,)
    return ()


def abandon_lacks(read: str) -> tuple[str, ...]:
    """Name what the abandonment of an import lacks: one that wrote or writes is kept (I-02)."""
    return (NOT_APPLIED,) if read in WRITING else ()


def commands_of(
    read: str, report: Mapping[str, Any] | None, *, contributor: bool
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """List the commands of an import, each with what it lacks, in the order of ``ImportCommand``.

    The quality on the project comes first, as for the commands of a project (WF-PRJ-0060): a
    reader who is no contributor sees each command, unavailable, naming it.
    """
    quality = () if contributor else (IS_CONTRIBUTOR,)
    return (
        ("apply", (*quality, *apply_lacks(read, report))),
        ("abandon", (*quality, *abandon_lacks(read))),
    )
