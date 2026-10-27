// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the correspondence of the extraction of the actual costs lacks, for the screens that offer
 * the import of actual costs (WF-REF-0190, US-0620): the project lists `import_actual_costs`
 * unavailable, naming `actual_cost_mapping_complete`; the columns without a label are the
 * correspondence's to say (`getActualCostMapping`, `missing_columns`), and only a session that may
 * read the cost settings (`cost_settings.read`) may read it — and be led to its page. Another reads
 * the condition alone, in the sentence of the unavailable command. A read the API refuses, or cannot
 * answer, is thrown for the pages of the shell to say.
 */
import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { leafOf } from "@/navigation/functions";
import type { Permission } from "@/session/request";

import type { ImportOffers, MappingGap } from "./offers";

/** The page of the correspondence of the extraction of the actual costs (FBS-3.1.3). */
const MAPPING_PAGE = leafOf("FBS-3.1.3");

/**
 * The gap of the correspondence, when the import of actual costs is unavailable for want of it and
 * the session may read it; none otherwise.
 */
export async function readMappingGap(
  offers: ImportOffers,
  permissions: readonly Permission[] | undefined,
): Promise<MappingGap | undefined> {
  const waits = offers.actual_costs?.missing_conditions.includes("actual_cost_mapping_complete");
  if (waits !== true || permissions?.includes("cost_settings.read") !== true) {
    return undefined;
  }
  const mapping = await readOrFail("getActualCostMapping", () =>
    serverClient().GET("/reference/actual-cost-mapping"),
  );
  return { columns: mapping.missing_columns, href: MAPPING_PAGE.route };
}
