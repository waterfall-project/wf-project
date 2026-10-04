// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The request of an export (WF-INTF-0050, WF-INTF-0110, WF-INTF-0130, WF-PLA-0120): the kind of
 * file chosen — and, for the image of the tree of tasks, the level it stops at, if the user gives
 * one —, in the revision the screen reads in — or, without one, the revision the server takes —,
 * asked by a server action. The API gives the hand back at once with a background task
 * (WF-ARC-0090), handed to the tracker of the shell with the request itself, which runs it again
 * if it fails; its result, a file made on demand and not kept (WF-DAT-0120), is downloaded from
 * the tracker once the task has succeeded. A refusal is told under the form (`OutcomeNotice`).
 */
"use client";

import { FileDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState, useTransition } from "react";

import { type ExportRequest, requestFileExport } from "@/api/actions/exchanges";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";

type ExportKind = ExportRequest["kind"];

/** The kinds of file an export makes, in the order of the contract. */
const EXPORT_KINDS: readonly ExportKind[] = [
  "ms_project_schedule",
  "estimate",
  "remaining",
  "task_tree_image",
];

/** Whether a value of the list is a kind of export. */
function isExportKind(value: string): value is ExportKind {
  return (EXPORT_KINDS as readonly string[]).includes(value);
}

/** Ask for an export of the project, and hand its task over to the tracker. */
export function ExportForm({
  projectId,
  revisionId,
}: {
  readonly projectId: string;
  /** The revision the screen reads in; none, and the server takes its own. */
  readonly revisionId: string | undefined;
}) {
  const t = useTranslations();
  const track = useTrackTask();
  const field = useId();
  const [kind, setKind] = useState<ExportKind>("ms_project_schedule");
  const [depth, setDepth] = useState("");
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    // The level of the image of the tree, when the user gives one; the server's otherwise.
    const level =
      kind === "task_tree_image" && /^[1-9]\d*$/.test(depth) && Number.isSafeInteger(Number(depth))
        ? Number(depth)
        : null;
    const request: ExportRequest = {
      kind,
      revision_id: revisionId ?? null,
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
            {EXPORT_KINDS.map((value) => (
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
        <Button type="submit" size="sm" variant="outline">
          <FileDown aria-hidden="true" />
          {t("exchanges.export.request")}
        </Button>
      </div>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </form>
  );
}
