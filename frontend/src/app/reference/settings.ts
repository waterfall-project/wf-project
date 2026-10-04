// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings every project inherits from the installation, as the screens of the reference data
 * read them (`getReferenceSettings`): the currency, the risk matrix, the thresholds of the indices,
 * the delay between two reviews. A read the API refuses, or cannot answer, is thrown for the pages
 * of the shell to say.
 */
import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";

/** Read the settings of the installation. */
export function readReferenceSettings() {
  return readOrFail("getReferenceSettings", () => serverClient().GET("/reference/settings"));
}
