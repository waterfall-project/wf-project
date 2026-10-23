// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The contractualisation of an amendment (US-0510, WF-REV-0050), from the grid of its differential:
 * the command opens a confirmation in the page, which first reads the report of the merge
 * (`getStructureMergeReport`) and presents it — the tasks, the lines and the links added, modified and
 * removed, in the marks `+`, `-`, `M` of the diff of the grids; the tasks started that the merge will
 * complete; the motives that refuse it, with which the merge is not offered —, then asks the version
 * name the revision produced bears, and confirms with the two counters the report read
 * (`mergeCostStructure`). Abandoning sends nothing: the report is a read. A report gone stale (412)
 * offers to read it anew, and the form keeps the name typed. The merge is handed to the worker: the
 * tracker of the shell follows it (WF-IHM-0080), and once it has succeeded the screen says which
 * revision is the reference now.
 *
 * The front computes nothing of the report: the lists are in the order received, the counts are the
 * lengths of what the server rendered.
 */
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import { type AmendmentMerge, mergeAmendment, readMergeReport } from "@/api/actions/revisions";
import type { components } from "@/api/generated/schema";
import type { BackgroundTask, Outcome } from "@/api/problem";
import { ConfirmedCommand } from "@/components/commands/confirmed-command";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import { type ObjectNames, OutcomeNotice } from "@/components/commands/outcome-notice";
import { Differences } from "@/components/exchanges/import-report";
import { DiffMark } from "@/components/grid/diff-mark";
import { DoneNotice } from "@/components/notices/done-notice";
import { useTrackTask, useWhenTaskSucceeds } from "@/components/tasks/task-tracker";
import { problemMessage } from "@/i18n/problem";

type Report = components["schemas"]["StructureMergeReport"];
type Change = Report["differences"][number]["change"];
type Target = Report["differences"][number]["target"];

/** The amendment a merge is about, and where it is. */
export interface MergedAmendment {
  readonly projectId: string;
  readonly revisionId: string;
  readonly structureId: string;
  readonly label: string;
}

/** The objects a report counts, in the order it presents them. */
const COUNTED: readonly Exclude<Target, "actual_cost_line">[] = ["task", "estimate_line", "link"];

/** The changes a report counts, each with the mark of the diff it bears. */
const COUNTED_CHANGES: readonly {
  readonly change: Change;
  readonly key: "added" | "updated" | "removed";
  readonly mark: "added" | "modified" | "removed";
}[] = [
  { change: "added", key: "added", mark: "added" },
  { change: "updated", key: "updated", mark: "modified" },
  { change: "removed", key: "removed", mark: "removed" },
];

const FIELD =
  "h-9 w-full max-w-sm rounded-md border border-input bg-background px-2 text-foreground";
const HEADING = "text-sm font-semibold";

/** The counts of what the merge adds, modifies and removes, by object, in the marks of the diff. */
function Counts({ report }: { readonly report: Report }) {
  const t = useTranslations("mergeReport");
  const targets = useTranslations("mergeReport.targets");
  return (
    <ul aria-label={t("counts")} className="space-y-0.5">
      {COUNTED.map((target) => (
        <li key={target} className="flex flex-wrap items-center gap-x-3">
          <span className="font-medium">{targets(target)}</span>
          {COUNTED_CHANGES.map(({ change, key, mark }) => {
            const count = report.differences.filter(
              (one) => one.target === target && one.change === change,
            ).length;
            return (
              <span key={change} className="inline-flex items-center gap-1 tabular-nums">
                <DiffMark difference={mark} />
                <span>{t(key, { count })}</span>
              </span>
            );
          })}
        </li>
      ))}
    </ul>
  );
}

/** The report of the merge as the server read it, and the motives that refuse it. */
function ReportBody({ report }: { readonly report: Report }) {
  const t = useTranslations("mergeReport");
  const locale = useLocale();
  const messages = useMessages();
  return (
    <div className="space-y-3">
      <Counts report={report} />
      {report.completed_tasks.length === 0 ? null : (
        <div className="space-y-1">
          <h3 className={HEADING}>{t("completed", { count: report.completed_tasks.length })}</h3>
          <ul className="list-inside list-disc">
            {report.completed_tasks.map((task) => (
              <li key={task.lineage_id}>{t("completedTask", { label: task.label })}</li>
            ))}
          </ul>
        </div>
      )}
      {report.refusals.length === 0 ? null : (
        <div role="alert" className="space-y-1 text-destructive">
          <h3 className={HEADING}>{t("refusals", { count: report.refusals.length })}</h3>
          <ul className="list-inside list-disc">
            {report.refusals.map((refusal, index) => (
              <li key={`${refusal.code}-${String(index)}`}>
                {problemMessage(refusal, { locale, messages })}
              </li>
            ))}
          </ul>
        </div>
      )}
      <Differences differences={report.differences} marks />
    </div>
  );
}

/** What the form shows of the report, read when it opens and read anew on demand. */
function ReportPanel({
  amendment,
  attempt,
  report,
  onRead,
  name,
  onName,
  names,
}: {
  readonly amendment: MergedAmendment;
  readonly attempt: number;
  readonly report: Outcome<Report> | undefined;
  readonly onRead: (report: Outcome<Report> | undefined) => void;
  readonly name: string;
  readonly onName: (name: string) => void;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("mergeReport");
  const field = useId();
  const { projectId, revisionId, structureId } = amendment;
  useEffect(() => {
    let current = true;
    onRead(undefined);
    void readMergeReport(projectId, revisionId, structureId).then((read) => {
      if (current) {
        onRead(read);
      }
    });
    return () => {
      current = false;
    };
  }, [projectId, revisionId, structureId, attempt, onRead]);
  return (
    <div className="space-y-3">
      <section aria-label={t("title")} aria-busy={report === undefined} className="space-y-2">
        <h2 className={HEADING}>{t("title")}</h2>
        {report === undefined ? <p role="status">{t("reading")}</p> : null}
        {report?.kind === "done" ? <ReportBody report={report.data} /> : null}
        {report !== undefined && report.kind !== "done" ? (
          <OutcomeNotice
            outcome={report}
            names={names}
            subject={amendment.label}
            onClear={() => {
              onRead(undefined);
            }}
          />
        ) : null}
      </section>
      <div className="space-y-1">
        <label htmlFor={field} className="block text-sm font-medium">
          {t("versionName")}
        </label>
        <input
          id={field}
          value={name}
          required
          maxLength={100}
          aria-describedby={`${field}-hint`}
          onChange={(event) => {
            onName(event.target.value);
          }}
          className={FIELD}
        />
        <p id={`${field}-hint`} className="text-xs text-muted-foreground">
          {t("versionNameHint")}
        </p>
      </div>
    </div>
  );
}

/** A merge handed to the worker: its task, the version name it bears, and the command that runs it again. */
interface Merged {
  readonly task: BackgroundTask;
  readonly version: string;
  readonly command: () => Promise<Outcome<BackgroundTask>>;
}

/**
 * Hand the merge to the tracker of the shell, once, and wait for its end: it is mounted by the
 * confirmation alone, so that a screen that offers the command needs the tracker only to follow a
 * merge. When the task has succeeded the screen is read again, and tells the reference.
 */
function Following({
  merged,
  onSucceeded,
}: {
  readonly merged: Merged;
  readonly onSucceeded: (version: string) => void;
}) {
  const router = useRouter();
  const track = useTrackTask();
  const handed = useRef(false);
  useEffect(() => {
    if (!handed.current) {
      handed.current = true;
      track(merged.task, { command: merged.command, subject: merged.version });
    }
  }, [track, merged]);
  useWhenTaskSucceeds(merged.task.task_id, () => {
    onSucceeded(merged.version);
    router.refresh();
  });
  return null;
}

/** Offer the contractualisation of the amendment a grid reads, as the revision lists it. */
export function MergeAmendmentCommand({
  offer,
  amendment,
  merged,
  names,
}: {
  readonly offer: CommandOffer | undefined;
  readonly amendment: MergedAmendment;
  /** Whether the amendment is merged already: the command is then no more presented. */
  readonly merged: boolean;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("mergeReport");
  const [report, setReport] = useState<Outcome<Report>>();
  const [attempt, setAttempt] = useState(0);
  const [name, setName] = useState("");
  const [followed, setFollowed] = useState<Merged>();
  const [reference, setReference] = useState<{ readonly version: string }>();
  const revisions = useRef<HTMLAnchorElement>(null);
  // The follow-up does not survive a full reload of the page, and need not: `merged`, read anew
  // by the next render, says the amendment is merged and the command is no more presented.
  // Once the page read again has taken the command away, the button that held the focus is gone:
  // the focus goes to the way on that the reference notice offers, if it fell on the page.
  useEffect(() => {
    if (
      merged &&
      reference !== undefined &&
      (document.activeElement === document.body || document.activeElement === null)
    ) {
      revisions.current?.focus();
    }
  }, [merged, reference]);
  const read = report?.kind === "done" ? report.data : undefined;
  const merge: AmendmentMerge | undefined =
    read === undefined
      ? undefined
      : {
          versionName: name.trim(),
          mainStructureLockVersion: read.main_structure_lock_version,
          amendmentLockVersion: read.amendment_lock_version,
        };
  const { projectId, revisionId, structureId } = amendment;
  const run = () =>
    merge === undefined
      ? Promise.reject(new Error("the merge is confirmed once its report is read"))
      : mergeAmendment(projectId, revisionId, structureId, merge);
  // Kept as it was confirmed: what the form holds later is another report's.
  const onRead = useCallback((next: Outcome<Report> | undefined) => {
    setReport(next);
  }, []);
  if (offer === undefined) {
    return null;
  }
  return (
    <div className="space-y-2">
      <ConfirmedCommand
        offer={offer}
        presented={!merged}
        label={t("label")}
        icon={commandIcon(REVISION_COMMAND_ICONS.merge_structure)}
        statement={t("statement")}
        submit={t("submit")}
        ready={merge !== undefined && read?.refusals.length === 0 && name.trim() !== ""}
        names={names}
        subject={amendment.label}
        run={run}
        done={() => t("queued", { version: name.trim() })}
        onDone={(task) => {
          setFollowed({ task, version: name.trim(), command: run });
        }}
        reread={{
          label: t("reread"),
          run: () => {
            setAttempt(attempt + 1);
          },
        }}
      >
        <ReportPanel
          amendment={amendment}
          attempt={attempt}
          report={report}
          onRead={onRead}
          name={name}
          onName={setName}
          names={names}
        />
      </ConfirmedCommand>
      {followed === undefined ? null : (
        <Following
          key={followed.task.task_id}
          merged={followed}
          onSucceeded={(version) => {
            setReference({ version });
          }}
        />
      )}
      <DoneNotice
        title={reference === undefined ? undefined : t("reference", reference)}
        of={reference}
      >
        <Link ref={revisions} href={`/projects/${projectId}/revisions`} className="underline">
          {t("seeRevisions")}
        </Link>
      </DoneNotice>
    </div>
  );
}
