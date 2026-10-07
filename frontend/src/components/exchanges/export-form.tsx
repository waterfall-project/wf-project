// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The request of an export (WF-INTF-0050, WF-INTF-0110, WF-INTF-0130, WF-PLA-0120): the kind of
 * file chosen among those the revision read offers to export (WF-IHM-0090) — and, for the image
 * of the tree of tasks, the level it stops at, if the user gives one —, asked by a server action.
 * An export is present or absent — the permission to read its kind guards it, and it lacks no
 * condition, a terminal project included (WF-CYC-0110) —: a kind the revision does not list is
 * not offered; one it would list unavailable would stay, the request naming what it lacks. The
 * API gives the hand back at once with a background task (WF-ARC-0090), handed to the tracker of
 * the shell with the request itself, which runs it again if it fails; its result, a file made on
 * demand and not kept (WF-DAT-0120), is downloaded from the tracker once the task has succeeded.
 * A refusal is told under the form (`OutcomeNotice`).
 */
"use client";

import { FileDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState, useTransition } from "react";

import { type ExportRequest, requestFileExport } from "@/api/actions/exchanges";
import type { Outcome } from "@/api/problem";
import { UnmetConditions } from "@/components/commands/command";
import { UNAVAILABLE, unmetId } from "@/components/commands/offer";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";

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
  const unmet = offer === undefined ? undefined : unmetId(offer, field);
  const [depth, setDepth] = useState("");
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending || offer?.is_available !== true) {
      return;
    }
    // The level of the image of the tree, when the user gives one; the server's otherwise.
    const level =
      kind === "task_tree_image" && /^[1-9]\d*$/.test(depth) && Number.isSafeInteger(Number(depth))
        ? Number(depth)
        : null;
    const request: ExportRequest = {
      kind,
      revision_id: revisionId,
      ...(kind === "task_tree_image" ? { depth: level } : {}),
    };
    const command = () => requestFileExport(projectId, request);
    startTransition(async () => {
      const result = await command();
      if (result.kind === "done") {
        setOutcome(undefined);
        track(result.data, { command, subject: t(`enums.ExportRequest.kind.${kind}`) });
      } else {
        setOutcome(result);
      }
    });
  };
  return (
    <form
      aria-label={t("exchanges.export.title")}
      aria-busy={pending}
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
              }
            }}
          >
            {offered.map((value) => (
              <option key={value} value={value}>
                {t(`enums.ExportRequest.kind.${value}`)}
              </option>
            ))}
          </NativeSelect>
        </div>
        {kind === "task_tree_image" ? (
          <label className="flex items-center gap-2 text-sm">
            {t("exchanges.export.depth")}
            <input
              type="number"
              min={1}
              step={1}
              inputMode="numeric"
              value={depth}
              onChange={(event) => {
                setDepth(event.target.value);
              }}
              className="h-8 w-20 rounded-md border border-input bg-background px-2 text-foreground"
            />
          </label>
        ) : null}
        <Button
          type="submit"
          size="sm"
          variant="outline"
          aria-disabled={offer?.is_available === true ? undefined : true}
          aria-describedby={unmet}
          className={UNAVAILABLE}
        >
          <FileDown aria-hidden="true" />
          {t("exchanges.export.request")}
        </Button>
      </div>
      {offer === undefined ? null : <UnmetConditions id={unmet} offer={offer} />}
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </form>
  );
}
