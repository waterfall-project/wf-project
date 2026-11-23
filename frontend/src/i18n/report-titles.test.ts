// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The titles of the reports of the catalogue open with the same words: `frontend/e2e/exchanges.spec.ts`
 * (`ANY_REPORT`) keeps the first two words of the title of the report of an import to assert that no
 * report of any kind is shown. A catalogue that renamed one of these titles without that common
 * beginning would leave the assertion counting zero regions, true for nothing (#4299).
 */
import { describe, expect, it } from "vitest";

import fr from "../../messages/fr.json";
import { firstWords } from "./report-titles";

/** The title of every report an e2e path asserts the absence of, by the screen that shows it. */
const TITLES = {
  update: fr.rebaseReport.title,
  merge: fr.mergeReport.title,
  occurrence: fr.riskOccurrenceReport.title,
  import: fr.exchanges.report.title,
};

describe("the titles of the reports of the catalogue", () => {
  it("begin with the words the exchanges path keeps to tell any report apart (#4299) [WF-QUA-0010-A]", () => {
    const common = firstWords(TITLES.import);
    expect(common.split(" ")).toHaveLength(2);
    for (const [report, title] of Object.entries(TITLES)) {
      expect(title.startsWith(common), `the title of the report of the ${report}`).toBe(true);
    }
  });
});
