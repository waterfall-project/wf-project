// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

/** Ask for the sign-in route, with the query a refusal for want of a session writes. */
function login(query = ""): Response {
  return GET(new Request(`http://front.example/login${query}`));
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the sign-in route", () => {
  it("leads on the fake back to the screen the 401 was aimed at", () => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
    const response = login(`?next=${encodeURIComponent("/projects/p1/lifecycle?tab=2")}`);
    expect(response.status).toBe(307);
    expect(response.headers.get("Location")).toBe("/projects/p1/lifecycle?tab=2");
  });

  it.each(["", "?next=https://elsewhere.example/", "?next=//elsewhere.example/"])(
    "leads to the home page when the query names no screen of this front: %j",
    (query) => {
      vi.stubEnv("WATERFALL_AUTH", "mock");
      expect(login(query).headers.get("Location")).toBe("/");
    },
  );

  it("answers nothing else yet, where a redirect would loop", () => {
    vi.stubEnv("WATERFALL_AUTH", undefined);
    expect(login("?next=/").status).toBe(501);
  });
});
