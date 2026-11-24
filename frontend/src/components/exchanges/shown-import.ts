// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The import whose report a screen shows: the one its address names (`import`), read from the API
 * (`getImport`) — none when the address names none an identifier can stand for, and gone when the
 * API does not know the one it names: the purge deleted it at its expiry or its abandonment
 * (WF-DAT-0080), which the screen says instead of failing (US-3280). Any other read the API
 * refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { components } from "@/api/generated/schema";
import { readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { isIdentifier, type SearchParameters } from "@/navigation/context";

import { IMPORT_PARAMETER } from "./offers";

type ImportDetail = components["schemas"]["ImportDetail"];

/** What the address names of an import: none, one the API read, or one that is gone. */
export type ShownImport =
  | { readonly kind: "none" }
  | { readonly kind: "read"; readonly entry: ImportDetail }
  | { readonly kind: "purged"; readonly importId: string };

/** The import to show the report of, if the address names one the API read. */
export function readEntry(shown: ShownImport): ImportDetail | undefined {
  return shown.kind === "read" ? shown.entry : undefined;
}

/** The identifier of the import the address names, read or gone; none when it names none. */
export function namedImport(shown: ShownImport): string | undefined {
  if (shown.kind === "read") {
    return shown.entry.import_id;
  }
  return shown.kind === "purged" ? shown.importId : undefined;
}

/**
 * Read the import the address names, when it names one an identifier can stand for. A 404 is the
 * import gone — or not the project's, which the API answers alike (WF-ADM-0110).
 */
export async function readShownImport(
  projectId: string,
  address: SearchParameters,
): Promise<ShownImport> {
  const importId = address.get(IMPORT_PARAMETER) ?? "";
  if (!isIdentifier(importId)) {
    return { kind: "none" };
  }
  const read = await readOrRefused("getImport", [{ status: 404 }], () =>
    serverClient().GET("/projects/{project_id}/imports/{import_id}", {
      params: { path: { project_id: projectId, import_id: importId } },
    }),
  );
  return read.kind === "read" ? { kind: "read", entry: read.data } : { kind: "purged", importId };
}
