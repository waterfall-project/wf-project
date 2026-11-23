// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What « Réexaminer » and « Déclarer survenu » do first for a risk whose own estimate is in arrears or
 * pruned (US-3140, WF-RIS-0070): the service refuses the review that keeps the risk identified and the
 * report of the occurrence until the own estimate is whole and up to date, and the risk says so by the
 * conditions its command lacks (`own_estimate_whole`, `own_estimate_up_to_date`, `lateOf`). The command
 * stays pressable then, and its press starts the step (`OwnEstimateStep`) instead of its form: the own
 * estimate is recomposed when it is pruned, then its update is read and, when it signals nothing,
 * applied without a question — the risk is read again, its severity recomputed, and the command goes on
 * with it. An update that keeps a value against the project is presented, with the severity and the
 * provision it recomputes, to confirm; one that is refused says what is to correct in the own estimate.
 * A review may leave the risk dismissed without the update (`onSkip`): it asks none, so the step
 * starts by the choice — update, or dismiss without — and writes nothing before it, the dismissal
 * staying possible once the update failed.
 *
 * The front decides none of it but by the conditions the risk lists and the word of the report.
 */
"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import { readRisk } from "@/api/actions/risks";
import { recomposeStructure, rebaseStructure } from "@/api/actions/revisions";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { type CommandOffer } from "@/components/commands/offer";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { STRUCTURE_PARAMETER } from "@/components/context/structure";
import { filterHref } from "@/components/grid/filters";
import { type Refused, settleOwnEstimate } from "@/components/revisions/own-estimate-settle";
import { type Report, ReportBody } from "@/components/revisions/rebase-report";
import { Button } from "@/components/ui/button";

/** A risk, as the contract gives it. */
type Risk = components["schemas"]["Risk"];

/** The conditions of the own estimate that the risk lists last on `review` and `declare_occurrence`. */
const OWN_ESTIMATE = new Set<string>(["own_estimate_whole", "own_estimate_up_to_date"]);

/** The offer of a command made available, which the step leaves the user to press. */
export const PRESSABLE: CommandOffer = { is_available: true, missing_conditions: [] };

/**
 * Whether the listing of the risk has announced its command available since the own estimate was
 * updated, `stamp` naming that update (none before one). The update is held as made until then, the
 * listing read anew not yet saying so; once it has, a listing that says the own estimate late again —
 * the main structure having moved, the risk keeping the counter it had — is a new lateness, which the
 * update made before does not cover.
 */
export function useListedSince(stamp: object | undefined, late: boolean): boolean {
  const [seen, setSeen] = useState<object>();
  const caught = stamp !== undefined && seen === stamp;
  if (stamp !== undefined && !late && !caught) {
    // Adjusted while rendering, as React admits for a state derived from the props that change.
    setSeen(stamp);
  }
  return caught;
}

/** What a command lacks of its own estimate, when that is all it lacks. */
export interface Lateness {
  /** Whether the command lacks the own estimate, and nothing else. */
  readonly late: boolean;
  /** Whether the own estimate is pruned, and is recomposed first. */
  readonly pruned: boolean;
}

/** Whether the own estimate is the sole reason the command is unavailable. */
export function lateOf(offer: CommandOffer | undefined): Lateness {
  const missing = offer?.missing_conditions ?? [];
  const late =
    offer !== undefined &&
    !offer.is_available &&
    missing.length > 0 &&
    missing.every((condition) => OWN_ESTIMATE.has(condition));
  return { late, pruned: late && missing.includes("own_estimate_whole") };
}

/** What the step shows: the choice, working, the report to confirm or to correct, or what refused. */
type Phase =
  | { readonly kind: "asking" }
  | { readonly kind: "working"; readonly step: "recomposing" | "updating" }
  | { readonly kind: "presented"; readonly report: Report; readonly outcome?: Outcome<unknown> }
  | { readonly kind: "failed"; readonly outcome: Refused };

/**
 * The address of the estimate of a structure: the address of the estimate of the revision, its
 * reading context kept, and the structure the server named.
 */
export function estimateOf(base: string, structure: string): string {
  const [path = "", query = ""] = base.split("?");
  return filterHref(path, new URLSearchParams(query), STRUCTURE_PARAMETER, structure);
}

/** The props of the step. */
export interface OwnEstimateStepProps {
  readonly projectId: string;
  readonly revisionId: string;
  readonly risk: Risk;
  /** Whether the own estimate is pruned: it is recomposed first. */
  readonly pruned: boolean;
  /** The own estimate is up to date; the risk read again, none when it could not be read. */
  readonly onReady: (fresh: Risk | undefined) => void;
  /** The step is left, nothing more asked. */
  readonly onClose: () => void;
  /**
   * The command goes on without the update, which it does not need (a review that dismisses). Given,
   * the step asks first, and writes nothing until the update is chosen: dismissing is possible before
   * it and, the update failed or refused, after it.
   */
  readonly onSkip?: (() => void) | undefined;
  /** The identifier of the step, which the command that opens it controls. */
  readonly id?: string | undefined;
  /**
   * The address of the estimate of the revision, where a refused update is corrected: the step leads
   * to the grid of the own estimate of the risk. None for a session that may not read it.
   */
  readonly estimate?: string | undefined;
}

/** Recompose, read and update the own estimate of a risk before the command that waited for it. */
export function OwnEstimateStep({
  projectId,
  revisionId,
  risk,
  pruned,
  onReady,
  onClose,
  onSkip,
  id,
  estimate,
}: OwnEstimateStepProps) {
  const t = useTranslations("ownEstimateFirst");
  const { structure_id: structureId, label, risk_id: riskId } = risk;
  // A command that may go on without the update asks before it writes one.
  const asks = onSkip !== undefined;
  const [phase, setPhase] = useState<Phase>(
    asks ? { kind: "asking" } : { kind: "working", step: pruned ? "recomposing" : "updating" },
  );
  const [begun, setBegun] = useState(!asks);
  const [busy, setBusy] = useState(false);
  const alive = useRef(false);
  const started = useRef(false);
  const ready = useRef(onReady);
  useEffect(() => {
    ready.current = onReady;
  });
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  /** The own estimate is up to date: read the risk anew, and hand it over. */
  const finish = useCallback(async () => {
    const read = await readRisk(projectId, riskId, revisionId);
    if (!alive.current) {
      return;
    }
    if (read.kind === "done") {
      ready.current(read.data);
    } else {
      setPhase({ kind: "failed", outcome: read });
    }
  }, [projectId, riskId, revisionId]);

  /** Read the report of the update, apply it when it signals nothing, else present it. */
  const settle = useCallback(async () => {
    const settled = await settleOwnEstimate(projectId, revisionId, structureId);
    if (!alive.current) {
      return;
    }
    if (settled.kind === "failed") {
      setPhase({ kind: "failed", outcome: settled.outcome });
    } else if (settled.kind === "presented") {
      setPhase({ kind: "presented", report: settled.report });
    } else {
      await finish();
    }
  }, [projectId, revisionId, structureId, finish]);

  useEffect(() => {
    if (!begun || started.current) {
      return;
    }
    started.current = true;
    void (async () => {
      if (pruned) {
        const recomposed = await recomposeStructure(projectId, revisionId, structureId);
        if (recomposed.kind !== "done") {
          if (alive.current) {
            setPhase({ kind: "failed", outcome: recomposed });
          }
          return;
        }
        if (recomposed.data.is_up_to_date !== false) {
          await finish();
          return;
        }
        if (alive.current) {
          setPhase({ kind: "working", step: "updating" });
        }
      }
      await settle();
    })();
  }, [begun, pruned, projectId, revisionId, structureId, finish, settle]);

  const names = { [structureId]: label };
  const skip =
    onSkip === undefined ? null : (
      <Button type="button" variant="outline" size="sm" onClick={onSkip}>
        {t("skip")}
      </Button>
    );
  const close = (
    <Button type="button" variant="outline" size="sm" onClick={onClose}>
      {t("close")}
    </Button>
  );
  if (phase.kind === "asking") {
    return (
      <section
        id={id}
        aria-label={t("title")}
        className="max-w-xl space-y-2 rounded-md border p-3 text-sm"
      >
        <h2 className="text-sm font-semibold">{t("title")}</h2>
        <p>{t("ask", { label })}</p>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            onClick={() => {
              setPhase({ kind: "working", step: pruned ? "recomposing" : "updating" });
              setBegun(true);
            }}
          >
            {t("update")}
          </Button>
          {skip}
          {close}
        </div>
      </section>
    );
  }
  if (phase.kind === "working") {
    return (
      <p id={id} role="status">
        {t(phase.step, { label })}
      </p>
    );
  }
  if (phase.kind === "failed") {
    return (
      <div id={id} className="space-y-2">
        <OutcomeNotice outcome={phase.outcome} names={names} subject={label} onClear={onClose} />
        {skip}
      </div>
    );
  }
  const { report } = phase;
  const refused = report.refusals.length > 0;
  const idle = () => {
    if (alive.current) {
      setBusy(false);
    }
  };
  const confirm = () => {
    if (busy) {
      return;
    }
    setBusy(true);
    void rebaseStructure(projectId, revisionId, structureId, {
      mainStructureLockVersion: report.main_structure_lock_version,
      structureLockVersion: report.structure_lock_version,
    }).then(async (outcome) => {
      if (!alive.current) {
        return;
      }
      if (outcome.kind === "done") {
        await finish();
      } else {
        setPhase({ kind: "presented", report, outcome });
      }
      idle();
    });
  };
  return (
    <section
      id={id}
      aria-label={t("title")}
      className="max-w-xl space-y-2 rounded-md border p-3 text-sm"
    >
      <h2 className="text-sm font-semibold">{t("title")}</h2>
      <p>{t(refused ? "refused" : "keeps", { label })}</p>
      {refused && estimate !== undefined ? (
        <p>
          <Link className="underline" href={estimateOf(estimate, structureId)}>
            {t("openGrid")}
          </Link>
        </p>
      ) : null}
      <ReportBody report={report} nature="risk" />
      {phase.outcome === undefined ? null : (
        <OutcomeNotice
          outcome={phase.outcome}
          names={names}
          subject={label}
          // A stale counter (412) is not read again by the same ones: the report is read anew.
          reread={{
            label: t("reread"),
            run: () => {
              setPhase({ kind: "working", step: "updating" });
              void settle();
            },
          }}
          onClear={() => {
            setPhase({ kind: "presented", report });
          }}
        />
      )}
      <div className="flex flex-wrap gap-2">
        {refused ? null : (
          <Button type="button" size="sm" aria-disabled={busy ? true : undefined} onClick={confirm}>
            {t("confirm")}
          </Button>
        )}
        {skip}
        {close}
      </div>
    </section>
  );
}
