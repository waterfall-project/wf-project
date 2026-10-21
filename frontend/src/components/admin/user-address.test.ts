// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { readAuditFilters } from "./audit-address";
import { readAccountState, USER_ORIGINS, usersQuery, USERS_LIST } from "./user-address";

/** Every filter of the audit columns, each side of each period and each author. */
const EVERY_AUDIT = readAuditFilters(
  new URLSearchParams({
    created_at_from: "2026-01-01T00:00:00Z",
    created_at_to: "2026-02-01T00:00:00Z",
    created_by_user_id: "01926f3a-7c00-7000-8000-000000000301",
    created_by_kind: "user",
    updated_at_from: "2026-03-01T00:00:00Z",
    updated_at_to: "2026-04-01T00:00:00Z",
    updated_by_user_id: "01926f3a-7c00-7000-8000-000000000303",
    updated_by_kind: "platform",
  }),
);

describe("what the list of the accounts reads of its address", () => {
  it("holds every parameter the list asks of the server, but its page: a filter under way reads another list", () => {
    const query = usersQuery({
      query: { sort: { column: "email", order: "asc" }, search: "martin", size: undefined },
      origins: USER_ORIGINS.slice(0, 1),
      orgNode: "01926f3a-7c00-7000-8000-000000000471",
      accessRoles: ["01926f3a-7c00-7000-8000-000000000702"],
      active: false,
      audit: EVERY_AUDIT,
      offset: 50,
    });
    const asked = Object.keys(query).filter((name) => name !== USERS_LIST.page);
    expect(asked).toHaveLength(16);
    expect(USERS_LIST.reads).toEqual(expect.arrayContaining(asked));
  });

  it("reads the state the address names, an address that hid the deactivated accounts as the active ones alone", () => {
    expect(readAccountState(new URLSearchParams("is_active=false"))).toBe(false);
    expect(readAccountState(new URLSearchParams("include_inactive=false"))).toBe(true);
    expect(readAccountState(new URLSearchParams("include_inactive=false&is_active=false"))).toBe(
      false,
    );
    expect(readAccountState(new URLSearchParams("is_active=1"))).toBeUndefined();
    expect(readAccountState(new URLSearchParams())).toBeUndefined();
  });
});
