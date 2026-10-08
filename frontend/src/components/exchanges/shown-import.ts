// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The import whose report a screen shows: the one its address names (`import`), read from the API
 * (`getImport`) — none when the address names none an identifier can stand for. A read the API
 * refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { isIdentifier, type SearchParameters } from "@/navigation/context";

import { IMPORT_PARAMETER } from "./offers";

/** Read the import the address names, when it names one an identifier can stand for. */
export async function readShownImport(projectId: string, address: SearchParameters) {
  const importId = address.get(IMPORT_PARAMETER) ?? "";
  if (!isIdentifier(importId)) {
    return undefined;
  }
  return readOrFail("getImport", () =>
    serverClient().GET("/projects/{project_id}/imports/{import_id}", {
      params: { path: { project_id: projectId, import_id: importId } },
    }),
  );
}
