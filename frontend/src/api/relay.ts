// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the routes of the front that hand a file of the API on as a stream share — the result of a
 * task (`app/tasks/[taskId]/result`), a backup (`app/admin/backups/[backupId]/content`) —: the read
 * of the answer with its headers, the file handed on as an attachment never sniffed nor kept, and
 * the way back to the screen a refusal sends the browser to (#416).
 *
 * Neither server nor client: the routes alone import it, on the server.
 */
import type { ResultRefusal } from "@/components/tasks/result-refusal";

import { attachment } from "./disposition";
import { type Answer, decode, type Outcome } from "./problem";

/** An answer of the API that breaks the contract: the unexpected error of a bad gateway. */
export const BAD_GATEWAY: ResultRefusal = {
  kind: "refused",
  problem: { code: "INTERNAL_ERROR", status: 502 },
  conflictingObjectId: null,
};

/** Neither the browser nor anything between keeps the file, nor the way back of a refusal. */
const NOT_KEPT = "private, no-store";

/** A media type, its parameters aside, in lower case; empty when the API gives none. */
export function mediaType(type: string | null): string {
  return type?.split(";")[0]?.trim().toLowerCase() ?? "";
}

/** Call the API for a file, and decode its answer, keeping the headers it came with. */
export async function readFile<T>(
  call: () => Promise<Answer<T>>,
): Promise<{ readonly outcome: Outcome<T>; readonly headers: Headers | undefined }> {
  let headers: Headers | undefined;
  const outcome = await decode(async () => {
    const answer = await call();
    headers = answer.response.headers;
    return answer;
  });
  return { outcome, headers };
}

/** Send the browser back to a screen of the front, by a relative address nothing keeps. */
export function sentBack(location: string): Response {
  return new Response(null, {
    status: 303,
    headers: { location, "cache-control": NOT_KEPT },
  });
}

/**
 * Hand a file on as it comes, an attachment under its name, of its type, never sniffed nor kept;
 * of its length when one is given.
 */
export function handedOn(
  body: BodyInit | null,
  file: { readonly name: string; readonly type: string; readonly length?: string | undefined },
): Response {
  const headers = new Headers({
    "content-disposition": attachment(file.name),
    "content-type": file.type,
    "x-content-type-options": "nosniff",
    "cache-control": NOT_KEPT,
  });
  if (file.length !== undefined) {
    headers.set("content-length", file.length);
  }
  return new Response(body, { status: 200, headers });
}
