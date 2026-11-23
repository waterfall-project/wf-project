// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The own estimate of a risk in the grids of the planning and the estimate (US-3140, WF-RIS-0030,
 * WF-RIS-0070): what the screen does for it before and around the entries, which the user is not asked
 * for when the update signals nothing.
 *
 * - **At its opening**, an own estimate a marking pruned lists `recompose` available: the screen
 *   recomposes it (`recomposeCostStructure`), then updates it when the main structure has changed since,
 *   without a question when the report signals nothing.
 * - **Before the first entry** into an own estimate in arrears, the guard (`entry-guard.ts`) reads the
 *   report of the update (`getStructureRebaseReport`): it signals nothing, the update is applied
 *   (`rebaseCostStructure`) without a question; the report keeps a value against the project, it is
 *   presented to confirm, with the severity and the provision it recomputes; it refuses, the report
 *   says what is to correct in the own estimate. The entry is withheld in each case: the update
 *   rewrites the rows the write was built on — their counters, perhaps their very nodes, a line it
 *   removes —, and the grid reads them again (`readAnew`), so that a write sent from the rows before
 *   it would carry a version the service refuses, or a value never seen. The user enters the value
 *   anew, the rows being read again, and the update is not asked twice. Entries made while the report
 *   is read share the one reading and the one update.
 *
 * The front decides none of it but by the word of the structure and of the report (`signals`). The
 * component is mounted for one structure — its parent keys it by the structure —, and renders what it
 * says above its children, the grid.
 */
"use client";

import { useTranslations } from "next-intl";
import {
  type ReactNode,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { readRebaseReport, recomposeStructure, rebaseStructure } from "@/api/actions/revisions";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { DoneNotice } from "@/components/notices/done-notice";
import { Button } from "@/components/ui/button";

import { type EntryGuard, EntryGuardProvider, withheld } from "./entry-guard";
import { type Report, ReportBody, signals } from "./rebase-report";

/** The own estimate, and where it is. */
export interface OwnEstimate {
  readonly projectId: string;
  readonly revisionId: string;
  readonly structureId: string;
  readonly label: string;
}

/** What an action that gives nothing back answered, when it did not give it. */
type Refused = Exclude<Outcome<never>, { readonly kind: "done" }>;

/** What settling the update came to. */
type Settled =
  | { readonly kind: "updated" }
  | { readonly kind: "presented" }
  | { readonly kind: "failed"; readonly outcome: Refused };

/** The own estimate, whether it is in arrears and whether it waits for its recomposition. */
export interface OwnEstimateEntryProps {
  readonly estimate: OwnEstimate;
  /** Whether the structure lists its entries available once it is updated, and only then. */
  readonly late: boolean;
  /** Whether the structure lists `recompose` available. */
  readonly recompose: boolean;
  readonly children: ReactNode;
}

/** What a confirmation of the update holds: the report read, what it said, what followed. */
interface Prompt {
  readonly report: Report;
  readonly outcome: Outcome<unknown> | undefined;
}

/** Whether a write was refused for the own estimate being out of date: the service says it late. */
function refusedAsLate(outcome: Outcome<unknown>): boolean {
  return (
    outcome.kind !== "done" &&
    outcome.kind !== "unreachable" &&
    outcome.problem.code === "STATE_FORBIDS_OPERATION" &&
    outcome.problem.params?.missing_condition === "own_estimate_up_to_date"
  );
}

/** Guard the entries of an own estimate in arrears, and recompose one that is pruned. */
export function OwnEstimateEntry({ estimate, late, recompose, children }: OwnEstimateEntryProps) {
  const t = useTranslations("ownEstimateEntry");
  const { projectId, revisionId, structureId, label } = estimate;
  const [prompt, setPrompt] = useState<Prompt>();
  const [failed, setFailed] = useState<Outcome<unknown>>();
  const [working, setWorking] = useState<"recomposing" | "updating">();
  const [done, setDone] = useState<{ readonly title: string }>();
  const [busy, setBusy] = useState(false);
  // What the structure lists now, read by the guard at the time of the entry — a write held by the
  // grid before the page was read anew must not see the state of the page before (défaut n° 2): kept
  // at the commit, before any event can follow it.
  const live = useRef({ late, updated: false });
  useLayoutEffect(() => {
    if (live.current.late !== late) {
      live.current = { late, updated: false };
    }
  }, [late]);
  const alive = useRef(false);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  const settle = useCallback(async (): Promise<Settled> => {
    const read = await readRebaseReport(projectId, revisionId, structureId);
    if (read.kind !== "done") {
      return { kind: "failed", outcome: read };
    }
    if (signals(read.data)) {
      if (alive.current) {
        setPrompt({ report: read.data, outcome: undefined });
      }
      return { kind: "presented" };
    }
    const rebased = await rebaseStructure(projectId, revisionId, structureId, {
      mainStructureLockVersion: read.data.main_structure_lock_version,
      structureLockVersion: read.data.structure_lock_version,
    });
    if (rebased.kind !== "done") {
      return { kind: "failed", outcome: rebased };
    }
    live.current.updated = true;
    return { kind: "updated" };
  }, [projectId, revisionId, structureId]);

  // The reading and the update under way, which entries made meanwhile wait for instead of starting
  // their own: a second report read and a second update would be refused as stale.
  const settling = useRef<Promise<Settled>>(undefined);
  const settleOnce = useCallback((): Promise<Settled> => {
    settling.current ??= settle().finally(() => {
      settling.current = undefined;
    });
    return settling.current;
  }, [settle]);

  const guard = useCallback<EntryGuard>(
    async (write) => {
      const now = live.current;
      if (!now.late || now.updated) {
        const outcome = await write();
        if (refusedAsLate(outcome)) {
          // The service says it late: the next entry reads the report anew.
          live.current = { late: true, updated: false };
        }
        return outcome;
      }
      const settled = await settleOnce();
      if (settled.kind === "failed") {
        return settled.outcome;
      }
      if (settled.kind === "updated" && alive.current) {
        setDone({ title: t("done", { label }) });
      }
      return withheld();
    },
    [settleOnce, t, label],
  );

  const opened = useRef(false);
  useEffect(() => {
    if (!recompose || opened.current) {
      return;
    }
    opened.current = true;
    void (async () => {
      setWorking("recomposing");
      const recomposed = await recomposeStructure(projectId, revisionId, structureId);
      let refused: Refused | undefined;
      if (recomposed.kind !== "done") {
        refused = recomposed;
      } else if (recomposed.data.is_up_to_date === false) {
        setWorking("updating");
        live.current = { late: true, updated: false };
        const settled = await settleOnce();
        refused = settled.kind === "failed" ? settled.outcome : undefined;
      }
      if (!alive.current) {
        return;
      }
      if (refused !== undefined) {
        setFailed(refused);
      }
      setWorking(undefined);
    })();
  }, [recompose, projectId, revisionId, structureId, settleOnce]);

  const confirm = () => {
    if (prompt === undefined || busy) {
      return;
    }
    const { report } = prompt;
    setBusy(true);
    void rebaseStructure(projectId, revisionId, structureId, {
      mainStructureLockVersion: report.main_structure_lock_version,
      structureLockVersion: report.structure_lock_version,
    }).then((outcome) => {
      if (!alive.current) {
        return;
      }
      setBusy(false);
      if (outcome.kind === "done") {
        live.current.updated = true;
        setPrompt(undefined);
        setDone({ title: t("done", { label }) });
      } else {
        setPrompt({ report, outcome });
      }
    });
  };

  const names = useMemo(() => ({ [structureId]: label }), [structureId, label]);
  return (
    <EntryGuardProvider value={guard}>
      {working === undefined ? null : <p role="status">{t(working, { label })}</p>}
      {failed === undefined ? null : (
        <OutcomeNotice
          outcome={failed}
          names={names}
          subject={label}
          onClear={() => {
            setFailed(undefined);
          }}
        />
      )}
      {prompt === undefined ? null : (
        <section
          aria-label={t("title")}
          className="max-w-xl space-y-2 rounded-md border p-3 text-sm"
        >
          <h2 className="text-sm font-semibold">{t("title")}</h2>
          <p>{t(prompt.report.refusals.length === 0 ? "keeps" : "refused", { label })}</p>
          <ReportBody report={prompt.report} nature="risk" />
          {prompt.outcome === undefined ? null : (
            <OutcomeNotice
              outcome={prompt.outcome}
              names={names}
              subject={label}
              onClear={() => {
                setPrompt({ report: prompt.report, outcome: undefined });
              }}
            />
          )}
          <div className="flex gap-2">
            {prompt.report.refusals.length === 0 ? (
              <Button
                type="button"
                size="sm"
                aria-disabled={busy ? true : undefined}
                onClick={confirm}
              >
                {t("confirm")}
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setPrompt(undefined);
              }}
            >
              {t("close")}
            </Button>
          </div>
        </section>
      )}
      <DoneNotice title={done?.title} of={done} subject={label} />
      {children}
    </EntryGuardProvider>
  );
}
