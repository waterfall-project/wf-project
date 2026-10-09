// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { readAccountState, USER_ORIGINS, usersQuery, USERS_LIST } from "./user-address";

describe("what the list of the accounts reads of its address", () => {
  it("holds every parameter the list asks of the server, but its page: a filter under way reads another list", () => {
    const query = usersQuery({
      query: { sort: { column: "email", order: "asc" }, search: "martin" },
      origins: USER_ORIGINS.slice(0, 1),
      orgNode: "01926f3a-7c00-7000-8000-000000000471",
      accessRoles: ["01926f3a-7c00-7000-8000-000000000702"],
      active: false,
      offset: 50,
    });
    const asked = Object.keys(query).filter((name) => name !== USERS_LIST.page);
    expect(asked).toHaveLength(8);
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
