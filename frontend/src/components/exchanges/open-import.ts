// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The first step of an import once the file is chosen (WF-ARC-0100), which the form of the screen of
 * the imports and exports (`ImportCommands`) and the drop zone of the start of a project
 * (`FileDrop`) share: the file is deposited and its analysis opened by a server action, the task that
 * analyses it goes to the tracker of the shell (WF-ARC-0090), and the report of the import is shown by
 * the address — only if the screen is still the one the file was sent from.
 */
"use client";

import { useRouter } from "next/navigation";

import { type Import, type ImportAsked, openFileImport } from "@/api/actions/exchanges";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { useTrackTask } from "@/components/tasks/task-tracker";

import { importHref, shownScreen } from "./offers";

/**
 * The function that sends a file as an import of the project: its outcome, the report shown where the
 * screen started (`start`, its context kept) once the import is opened.
 */
export function useOpenImport(
  projectId: string,
  start: string,
): (asked: ImportAsked, file: File) => Promise<Outcome<Import>> {
  const track = useTrackTask();
  const router = useRouter();
  const held = useHeldCommand();
  return async (asked, file) => {
    const form = new FormData();
    form.set("file", file);
    const result = await held(openFileImport(projectId, asked, form));
    if (result.kind === "done") {
      const opened = result.data;
      if (opened.task !== undefined) {
        track(opened.task, { subject: opened.filename });
      }
      // The report is shown only if the screen is still the one the file was sent from.
      if (shownScreen() === start.split("?")[0]) {
        router.push(importHref(start, opened.import_id));
      }
    }
    return result;
  };
}
