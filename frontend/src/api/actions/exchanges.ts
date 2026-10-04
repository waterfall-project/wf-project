// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the exchanges by file (`uploadFile`, `openImport`, `applyImport`,
 * `abandonImport`, `requestExport`): an import in two steps (WF-ARC-0100) — the file deposited
 * then its analysis opened, which gives the import back at once; its application, confirmed,
 * which gives a background task back (WF-ARC-0090); or its abandonment — and the request of an
 * export, a background task too. The API judges each: the front decides nothing of the content.
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import {
  type BackgroundTask,
  decode,
  decodeTask,
  type Outcome,
  type Settled,
  settled,
} from "@/api/problem";
import { serverClient } from "@/api/server";

/** An import, and the report of its analysis once there is one. */
export type Import = components["schemas"]["Import"];

/** What a file is imported as: a planning, an estimate, a remaining, actual costs. */
export type ExchangeKind = components["schemas"]["ExchangeKind"];

/** What an export asks for. */
export type ExportRequest = components["schemas"]["ExportRequest"];

/**
 * Deposit the file of a form, then open its import as the kind chosen: the analysis is queued,
 * and the import comes back at once with the task that analyses it. A refusal of the deposit —
 * a file too large — stops there. A form without a file is no request of this front — its field
 * requires one —, and is not sent.
 */
export async function openFileImport(
  projectId: string,
  kind: ExchangeKind,
  form: FormData,
): Promise<Outcome<Import>> {
  const file = form.get("file");
  if (!(file instanceof Blob)) {
    throw new TypeError("an import opens on a file");
  }
  const upload = new FormData();
  upload.set("file", file);
  const deposited = await decode(() =>
    serverClient().POST("/file-uploads", {
      // The contract types the part of a file as a string: the form goes as it is, multipart.
      body: upload as unknown as { file: string },
    }),
  );
  if (deposited.kind !== "done") {
    return deposited;
  }
  return decode(() =>
    serverClient().POST("/projects/{project_id}/imports", {
      params: { path: { project_id: projectId } },
      body: { kind, upload_id: deposited.data.upload_id },
    }),
  );
}

/**
 * Apply an import the user confirmed: the API rechecks the rights and the state of the project
 * when it runs it, and gives a background task back at once. The screen is read anew: the import
 * no longer waits for its confirmation.
 */
export async function applyFileImport(
  projectId: string,
  importId: string,
): Promise<Outcome<BackgroundTask>> {
  const outcome = await decodeTask(() =>
    serverClient().POST("/projects/{project_id}/imports/{import_id}/apply", {
      params: { path: { project_id: projectId, import_id: importId } },
      body: { confirmed: true },
    }),
  );
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/** Abandon an import: the project is left unchanged, and its file deleted (WF-INTF-0080). */
export async function abandonFileImport(projectId: string, importId: string): Promise<Settled> {
  return settled(
    await decode(() =>
      serverClient().DELETE("/projects/{project_id}/imports/{import_id}", {
        params: { path: { project_id: projectId, import_id: importId } },
      }),
    ),
  );
}

/** Ask for an export: the file is made by a background task, whose result is then read. */
export async function requestFileExport(
  projectId: string,
  request: ExportRequest,
): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().POST("/projects/{project_id}/exports", {
      params: { path: { project_id: projectId } },
      body: request,
    }),
  );
}
