// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The drop zone of the file of an import of a planning (FBS-4.3.4, WF-INTF-0040), from the start of
 * a project: a file dragged onto the zone, or chosen from the keyboard by its button, which opens
 * the selector of the browser. The zone is announced — named, and described by the sentence that
 * says what it takes —, and the type of the file is checked before anything is sent: an MS Project
 * file is an XML file, and so is the size, past the largest an import takes (§4.6.2). A file that
 * passes goes the way the form of the screen of the imports and exports sends it (`useOpenImport`):
 * the deposit, the analysis in the tracker of the shell, then the report of the import on the
 * screen, to be applied or abandoned; a refusal is told under the zone (`OutcomeNotice`). The zone
 * says that it is sending, says a file dropped meanwhile is not taken, and takes no other once one
 * is sent — unless the task that analyses it fails, which frees the zone for another file —, nor
 * while the analysis of a file of the project it finds, mounted anew, runs (#3404). Once the address
 * has named the import sent and names it no more — abandoned, or another shown —, the zone takes a
 * new file and no longer says the last one is sent (WF-INTF-0080, #4429). The API judges the content.
 *
 * The zone is lit while a file is dragged over it, over its children too: the entries and the exits
 * of the drag are counted, as `relatedTarget` of a leave is null in Firefox.
 */
"use client";

import { FileUp, Upload } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { type DragEvent, useCallback, useId, useMemo, useRef, useState } from "react";

import type { Outcome } from "@/api/problem";
import { OutcomeNotice, useReadAnew } from "@/components/commands/outcome-notice";
import { WaitingIcon, waitingAttributes } from "@/components/commands/waiting";
import { useRunningTask, useTaskRunning, useWhenTaskFails } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";

import { IMPORT_MAX_BYTES, IMPORT_PARAMETER, MEBIBYTE } from "./offers";
import { analysisAim, useOpenImport } from "./open-import";

/** The extension of the file of an MS Project schedule. */
const EXTENSION = ".xml";

/**
 * What the zone says of the file given: not an XML file, or one past the largest an import takes.
 */
type FileProblem = "notXml" | "tooLarge";

/** What the zone says besides: a file dropped while another is being sent. */
type DropProblem = FileProblem | "busy";

/** What is wrong with a file before it is sent, if anything. */
function fileProblem(file: File): FileProblem | undefined {
  if (!file.name.toLowerCase().endsWith(EXTENSION)) {
    return "notXml";
  }
  return file.size > IMPORT_MAX_BYTES ? "tooLarge" : undefined;
}

/**
 * The import the file sent opened, followed by the address: once the address has named it and names
 * it no more, `free` runs, in the render that sees it, so that the zone takes a new file.
 */
function useSentImport(free: () => void) {
  const [sent, setSent] = useState<{ readonly id: string; readonly named: boolean }>();
  const addressed = useSearchParams().get(IMPORT_PARAMETER);
  if (sent !== undefined && !sent.named && addressed === sent.id) {
    setSent({ id: sent.id, named: true });
  } else if (sent?.named === true && addressed !== sent.id) {
    setSent(undefined);
    free();
  }
  // Stable between renders where nothing changes, for the callbacks that hold it.
  return useMemo(
    () => ({
      opened: (id: string) => {
        setSent({ id, named: false });
      },
      forget: () => {
        setSent(undefined);
      },
    }),
    [],
  );
}

/**
 * The drop zone of the file of the import of a planning, and the address it shows the report at.
 */
export function FileDrop({
  projectId,
  start,
}: {
  readonly projectId: string;
  /** The address of the screen, its context kept, from which the report of the import is shown. */
  readonly start: string;
}) {
  const t = useTranslations("exchanges.drop");
  const open = useOpenImport(projectId, start);
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [problem, setProblem] = useState<DropProblem>();
  // The file being sent, then the file sent: the zone takes no other until the report is shown.
  // Being sent from the drop to the answer, and lifted in the very update that tells it — not by a
  // transition, whose end would wait for every other async action of the page (#1484).
  const [sending, setSending] = useState<string>();
  const busy = sending !== undefined;
  const [sent, setSent] = useState<string>();
  // The task that analyses the file sent: its failure frees the zone.
  const [analysis, setAnalysis] = useState<string>();
  const sentImport = useSentImport(() => {
    setSent(undefined);
    setAnalysis(undefined);
  });
  // The button waits while the file is sent and while its analysis runs (WF-IHM-0080, #3279) —
  // mounted anew, while an analysis of the project runs (#3404).
  const found = useRunningTask(analysisAim(projectId));
  const analysing = useTaskRunning(analysis ?? found);
  // The drags that entered the zone or one of its children and did not leave yet.
  const depth = useRef(0);
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // A file lost once sent: the zone takes no other until the screen has been read anew (US-2240).
  const reading = useReadAnew(outcome);
  const waiting = busy || analysing || reading;

  useWhenTaskFails(
    analysis,
    useCallback(() => {
      setSent(undefined);
      sentImport.forget();
      setAnalysis(undefined);
    }, [sentImport]),
  );

  const receive = (file: File | undefined) => {
    // A file sent, or an analysis of the project found running once mounted anew: no other is
    // taken.
    if (file === undefined || sent !== undefined || analysing) {
      return;
    }
    if (busy || reading) {
      setProblem("busy");
      return;
    }
    const wrong = fileProblem(file);
    setProblem(wrong);
    setOutcome(undefined);
    if (wrong !== undefined) {
      return;
    }
    setSending(file.name);
    void open({ kind: "ms_project_schedule" }, file).then((result) => {
      setSending(undefined);
      setProblem(undefined);
      if (result.kind === "done") {
        setSent(file.name);
        sentImport.opened(result.data.import_id);
        setAnalysis(result.data.task?.task_id);
      } else {
        setOutcome(result);
      }
    });
  };
  const drop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault();
    depth.current = 0;
    setOver(false);
    receive(event.dataTransfer.files[0]);
  };

  return (
    <div
      role="group"
      aria-labelledby={`${id}-title`}
      aria-describedby={`${id}-hint`}
      aria-busy={busy || reading}
      onDragEnter={() => {
        depth.current += 1;
        setOver(true);
      }}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => {
        // Moving over a child of the zone enters it before it leaves the zone: only the last exit
        // leaves the zone for the user.
        depth.current = Math.max(0, depth.current - 1);
        if (depth.current === 0) {
          setOver(false);
        }
      }}
      onDrop={drop}
      className={`space-y-2 rounded-md border-2 border-dashed p-4 ${over ? "border-ring bg-accent" : ""}`}
    >
      <p id={`${id}-title`} className="flex items-center gap-2 text-sm font-medium">
        <FileUp aria-hidden="true" className="size-4 shrink-0" />
        {t("title")}
      </p>
      <p id={`${id}-hint`} className="text-sm text-muted-foreground">
        {t("hint", { max: IMPORT_MAX_BYTES / MEBIBYTE })}
      </p>
      <input
        ref={input}
        type="file"
        accept={`${EXTENSION},text/xml,application/xml`}
        aria-label={t("file")}
        tabIndex={-1}
        hidden
        onChange={(event) => {
          receive(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        {...waitingAttributes(waiting)}
        // A file sent whose analysis was not handed over: no other is taken, the button marked all
        // the same.
        {...(sent !== undefined ? { "aria-disabled": true } : {})}
        aria-describedby={problem === undefined ? undefined : `${id}-problem`}
        onClick={() => {
          if (!waiting && sent === undefined) {
            input.current?.click();
          }
        }}
      >
        <WaitingIcon waiting={waiting} icon={<Upload aria-hidden="true" />} />
        {t("choose")}
      </Button>
      {sending === undefined ? null : (
        <p role="status" className="text-sm text-muted-foreground">
          {t("sending", { file: sending })}
        </p>
      )}
      {sent === undefined ? null : (
        <p role="status" className="text-sm text-muted-foreground">
          {t("sent", { file: sent })}
        </p>
      )}
      {problem === undefined ? null : (
        <p id={`${id}-problem`} role="alert" className="text-sm text-destructive">
          {problem === "notXml"
            ? t("notXml")
            : problem === "busy"
              ? t("busy")
              : t("tooLarge", { max: IMPORT_MAX_BYTES / MEBIBYTE })}
        </p>
      )}
      <OutcomeNotice
        outcome={outcome}
        reading={reading}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </div>
  );
}
