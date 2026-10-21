// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { readAuditFilters } from "./audit-address";
import { rolesQuery } from "./role-address";

/** No filter of the audit columns. */
const NO_AUDIT = readAuditFilters(new URLSearchParams());

describe("what the list of the access roles asks the server", () => {
  it("asks the search, the sort, the kind and the bounds of the holders under the names of the contract", () => {
    expect(
      rolesQuery({
        query: { sort: { column: "holder_count", order: "desc" }, search: "chef", size: undefined },
        predefined: false,
        holders: { min: "1", max: "3" },
        audit: NO_AUDIT,
      }),
    ).toEqual({
      search: "chef",
      sort_by: "holder_count",
      sort_order: "desc",
      is_predefined: false,
      holder_count_min: 1,
      holder_count_max: 3,
    });
  });

  it("asks the bounds of the holders as the counts of the contract, nought included", () => {
    expect(
      rolesQuery({
        query: { sort: undefined, search: undefined, size: undefined },
        predefined: undefined,
        holders: { min: undefined, max: "0" },
        audit: NO_AUDIT,
      }),
    ).toEqual({ holder_count_max: 0 });
  });
});
