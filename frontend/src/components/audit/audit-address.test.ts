// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  ACTOR_KINDS,
  AUDIT_ACTIONS,
  AUDIT_LIST,
  type AuditFilters,
  auditQuery,
  OBJECT_KINDS,
} from "./audit-address";

const ID = "01926f3a-7c00-7000-8000-000000000001";

describe("what the journal reads of its address", () => {
  it("holds every parameter the journal asks of the server, but its page: a filter under way reads another list", () => {
    const every: AuditFilters = {
      from: "2026-05-01T00:00:00Z",
      to: "2026-06-01T00:00:00Z",
      user: ID,
      actorKinds: ACTOR_KINDS.slice(0, 1),
      actions: AUDIT_ACTIONS.slice(0, 2),
      project: ID,
      objectKind: OBJECT_KINDS[0],
      object: ID,
      correlation: "req-1",
    };
    const sorted = { sort: { column: "actor", order: "asc" }, search: "couts" } as const;
    const asked = Object.keys(auditQuery(every, sorted, undefined));
    expect(asked).toHaveLength(12);
    expect(AUDIT_LIST.reads).toEqual(expect.arrayContaining(asked));
  });
});
