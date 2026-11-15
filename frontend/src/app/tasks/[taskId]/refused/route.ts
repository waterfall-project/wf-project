// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The page with nothing in it a hidden frame is sent back to when the route of the result refuses
 * the file it was to download (`app/tasks/[taskId]/result`, #3297): the refusal is in its address
 * (`refused_task`, `refusal`), which the screen reads from the frame (`inFrame` of
 * `result-download.tsx`). It reads nothing of the API and renders nothing of the application: the
 * screen the download left from would be rendered whole, with its reads, to say one address. It
 * is no page to open: an empty document, never kept by a cache.
 */
import { NOT_KEPT } from "@/api/relay";

/** Answer an empty document, whatever the address says of the refusal. */
export function GET(): Response {
  return new Response("<!doctype html><title></title>", {
    status: 200,
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": NOT_KEPT },
  });
}
