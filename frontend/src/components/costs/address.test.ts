// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { COSTS_LIST, costsQuery } from "./address";

describe("what the list of the costs reads of its address", () => {
  it("holds every parameter the list asks of the server, but its page: a filter under way reads another list", () => {
    const query = costsQuery({
      offset: 50,
      subproject: "unassigned",
      filters: { scope: "excluded", from: "2026-04-01", to: "2026-04-30" },
      sort: { column: "amount", order: "desc" },
    });
    const asked = Object.keys(query).filter((name) => name !== COSTS_LIST.page);
    expect(asked).toHaveLength(6);
    expect(COSTS_LIST.reads).toEqual(expect.arrayContaining(asked));
  });
});
