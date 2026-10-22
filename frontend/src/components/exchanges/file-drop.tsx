// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The drop zone of the file of an import of a planning (FBS-4.3.4, WF-INTF-0040), from the start of a
 * project: a file dragged onto the zone, or chosen from the keyboard by its button, which opens the
 * selector of the browser. The zone is announced — named, and described by the sentence that says what
 * it takes —, and the type of the file is checked before anything is sent: an MS Project file is an XML
 * file, and so is the size, past the largest an import takes (§4.6.2). A file that passes goes the
 * way the form of the screen of the imports and exports sends it (`useOpenImport`): the deposit, the
 * analysis in the tracker of the shell, then the report of the import on the screen, to be applied or
 * abandoned; a refusal is told under the zone (`OutcomeNotice`). The API judges the content.
 */
"use client";

import { FileUp, Upload } from "lucide-react";
import { useTranslations } from "next-intl";
import { type DragEvent, useId, useRef, useState, useTransition } from "react";

import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";

import { IMPORT_MAX_BYTES, MEBIBYTE } from "./offers";
import { useOpenImport } from "./open-import";

/** The extension of the file of an MS Project schedule. */
const EXTENSION = ".xml";

/** What the zone says of the file given: not an XML file, or one past the largest an import takes. */
type FileProblem = "notXml" | "tooLarge";

/** What is wrong with a file before it is sent, if anything. */
export function fileProblem(file: File): FileProblem | undefined {
  if (!file.name.toLowerCase().endsWith(EXTENSION)) {
    return "notXml";
  }
  return file.size > IMPORT_MAX_BYTES ? "tooLarge" : undefined;
}

/** The drop zone of the file of the import of a planning, and the address it shows the report at. */
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
  const [problem, setProblem] = useState<FileProblem>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();

  const receive = (file: File | undefined) => {
    if (file === undefined || pending) {
      return;
    }
    const wrong = fileProblem(file);
    setProblem(wrong);
    setOutcome(undefined);
    if (wrong !== undefined) {
      return;
    }
    startTransition(async () => {
      const result = await open({ kind: "ms_project_schedule" }, file);
      if (result.kind !== "done") {
        setOutcome(result);
      }
    });
  };
  const drop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault();
    setOver(false);
    receive(event.dataTransfer.files[0]);
  };

  return (
    <div
      role="group"
      aria-labelledby={`${id}-title`}
      aria-describedby={`${id}-hint`}
      aria-busy={pending}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => {
        setOver(false);
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
        aria-disabled={pending ? true : undefined}
        aria-describedby={problem === undefined ? undefined : `${id}-problem`}
        onClick={() => {
          if (!pending) {
            input.current?.click();
          }
        }}
      >
        <Upload aria-hidden="true" />
        {t("choose")}
      </Button>
      {problem === undefined ? null : (
        <p id={`${id}-problem`} role="alert" className="text-sm text-destructive">
          {problem === "notXml" ? t("notXml") : t("tooLarge", { max: IMPORT_MAX_BYTES / MEBIBYTE })}
        </p>
      )}
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </div>
  );
}
