// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The request of an export (WF-INTF-0050, WF-INTF-0110, WF-INTF-0130, WF-PLA-0120): the kind of
 * file chosen among those the revision read offers to export (WF-IHM-0090) — and, for the image
 * of the tree of tasks, the level it stops at, and, for the remaining to commit, the date of the
 * review the file bears (WF-INTF-0130), if the user gives them —, asked by a server action.
 * An export is present or absent — the permission to read its kind guards it, and it lacks no
 * condition, a terminal project included (WF-CYC-0110) —: a kind the revision does not list is
 * not offered; one it would list unavailable would stay, the request naming what it lacks. The
 * API gives the hand back at once with a background task (WF-ARC-0090), handed to the tracker of
 * the shell with the request itself, which runs it again if it fails; its result, a file made on
 * demand and not kept (WF-DAT-0120), is downloaded by itself once the task has succeeded, if the
 * form still shows — from the card of its end, or from the tracker, otherwise (#3103).
 * The request waits, saying so, until the task ends (`waiting.tsx`, #3103) — mounted anew, the tab
 * reloaded or the screen left and come back to, until the export of the revision it finds still
 * running ends (`useRunningTask`, #3404) —: failed, it is given back.
 * A refusal is told under the form (`OutcomeNotice`).
 */
"use client";

import { FileDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState } from "react";

import { type ExportRequest, requestFileExport } from "@/api/actions/exchanges";
import type { Outcome } from "@/api/problem";
import { PressRefusal, useUnmet } from "@/components/commands/command";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { useHeldCommand } from "@/components/commands/held";
import { UNAVAILABLE } from "@/components/commands/offer";
import { OutcomeNotice, useReadAnew } from "@/components/commands/outcome-notice";
import { WaitingIcon, waitingAttributes } from "@/components/commands/waiting";
import {
  useDownloadWhenTaskSucceeds,
  useRunningTask,
  useTaskRunning,
  useTrackTask,
} from "@/components/tasks/task-tracker";
import { taskAim } from "@/components/tasks/tracking";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";

import { isPlanningDate } from "@/i18n/format";

import { EXPORT_KINDS, type ExportOffers } from "./offers";

type ExportKind = ExportRequest["kind"];

/** Whether a value of the list is a kind of export. */
function isExportKind(value: string): value is ExportKind {
  return (EXPORT_KINDS as readonly string[]).includes(value);
}

/** What the request of an export reads: the project, the revision read, and what it offers. */
export interface ExportFormProps {
  readonly projectId: string;
  /** The revision the screen reads in, which the export reads. */
  readonly revisionId: string;
  /** The export of each kind, as the revision read offers it. */
  readonly offers: ExportOffers;
}

/** Ask for an export of the revision read, and hand its task over to the tracker. */
export function ExportForm({ projectId, revisionId, offers }: ExportFormProps) {
  const t = useTranslations();
  const [first, ...others] = EXPORT_KINDS.filter((value) => offers[value] !== undefined);
  return first === undefined ? (
    <p className="text-sm text-muted-foreground">{t("exchanges.export.none")}</p>
  ) : (
    <OfferedExports
      projectId={projectId}
      revisionId={revisionId}
      offers={offers}
      offered={[first, ...others]}
    />
  );
}

/** The kinds of export offered, one at least, in the order of the contract. */
type OfferedKinds = readonly [ExportKind, ...ExportKind[]];

/** The request of an export among the kinds offered. */
function OfferedExports({
  projectId,
  revisionId,
  offers,
  offered,
}: ExportFormProps & { readonly offered: OfferedKinds }) {
  const t = useTranslations();
  const track = useTrackTask();
  const field = useId();
  const [chosen, setKind] = useState<ExportKind>();
  // The kind chosen while the revision still offers it; the first it offers otherwise.
  const kind = chosen !== undefined && offered.includes(chosen) ? chosen : offered[0];
  const offer = offers[kind];
  const unmet = useUnmet();
  // The presses of the request while the kind is unavailable: each says what it lacks.
  const [presses, setPresses] = useState(0);
  const [depth, setDepth] = useState("");
  const [reviewDate, setReviewDate] = useState("");
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // Busy from the request to the answer, and lifted in the very update that tells it — not a
  // transition, whose end would wait for every other async action of the page (#1484).
  const [busy, setBusy] = useState(false);
  // The task of the last export asked — else, mounted anew, the export of the revision that runs
  // (#3404): the request waits while it runs, given back at its end.
  const aim = taskAim("export", revisionId);
  const [exporting, setExporting] = useState<string>();
  const found = useRunningTask(aim);
  const running = useTaskRunning(exporting ?? found);
  // An export lost once sent: the request waits until the screen has been read anew (US-2240).
  const reading = useReadAnew(outcome);
  // Its file leaves by itself once made, while the form that asked it still shows (#3103): one found
  // again leaves from the card of its end, lest a form mounted after that end download it again.
  useDownloadWhenTaskSucceeds(exporting);
  const waiting = busy || running || reading;
  // A link clicked while the export is asked waits for it, and is not followed when refused.
  const held = useHeldCommand();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (offer?.is_available === false) {
      setPresses((count) => count + 1);
      return;
    }
    if (waiting || offer?.is_available !== true) {
      return;
    }
    // The level of the image of the tree, when the user gives one; the server's otherwise.
    const level =
      kind === "task_tree_image" && /^[1-9]\d*$/.test(depth) && Number.isSafeInteger(Number(depth))
        ? Number(depth)
        : null;
    // The date of the review of a remaining to commit, when the user gives one: the day of the
    // request otherwise, which the server chooses (WF-INTF-0130).
    const review = kind === "remaining" && isPlanningDate(reviewDate) ? reviewDate : null;
    const request: ExportRequest = {
      kind,
      revision_id: revisionId,
      ...(kind === "task_tree_image" ? { depth: level } : {}),
      ...(kind === "remaining" ? { review_date: review } : {}),
    };
    const command = () => requestFileExport(projectId, request);
    setBusy(true);
    void held(command()).then((result) => {
      setBusy(false);
      if (result.kind === "done") {
        track(result.data, { command, subject: t(`enums.ExportKind.${kind}`), aim });
        setExporting(result.data.task_id);
      }
      setOutcome(result.kind === "done" ? undefined : result);
    });
  };
  return (
    <form
      aria-label={t("exchanges.export.title")}
      aria-busy={busy}
      onSubmit={submit}
      className="space-y-2"
    >
      <label htmlFor={field} className="block text-sm font-medium">
        {t("exchanges.export.kind")}
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <div className="w-64">
          <NativeSelect
            id={field}
            value={kind}
            onChange={(event) => {
              if (isExportKind(event.target.value)) {
                setKind(event.target.value);
                // The presses were told of the kind left: the next kind starts without a refusal.
                setPresses(0);
              }
            }}
          >
            {offered.map((value) => (
              <option key={value} value={value}>
                {t(`enums.ExportKind.${value}`)}
              </option>
            ))}
          </NativeSelect>
        </div>
        {kind === "task_tree_image" ? (
          <label className="flex items-center gap-2 text-sm">
            {t("exchanges.export.depth")}
            <Input
              type="number"
              min={1}
              step={1}
              inputMode="numeric"
              value={depth}
              onChange={(event) => {
                setDepth(event.target.value);
              }}
              className="w-20"
            />
          </label>
        ) : null}
        {kind === "remaining" ? (
          <label className="flex items-center gap-2 text-sm">
            {t("exchanges.export.reviewDate")}
            <Input
              type="date"
              value={reviewDate}
              onChange={(event) => {
                setReviewDate(event.target.value);
              }}
              className="w-auto"
            />
          </label>
        ) : null}
        <CommandTooltip
          label={t("exchanges.export.request")}
          help={t("commands.exportRequest.help")}
          unavailable={offer === undefined || offer.is_available ? undefined : unmet(offer)}
        >
          <Button
            type="submit"
            size="sm"
            variant="outline"
            {...waitingAttributes(waiting)}
            {...(offer?.is_available === true ? {} : { "aria-disabled": true })}
            className={UNAVAILABLE}
          >
            <WaitingIcon waiting={waiting} icon={<FileDown aria-hidden="true" />} />
            {t("exchanges.export.request")}
          </Button>
        </CommandTooltip>
      </div>
      {offer === undefined ? null : <PressRefusal offer={offer} presses={presses} />}
      <OutcomeNotice
        outcome={outcome}
        reading={reading}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </form>
  );
}
