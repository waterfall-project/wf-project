// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { GET as apiPath } from "@/app/api/v1/metrics/route";
import { GET as rootPath } from "@/app/metrics/route";

describe("the public door at the point of metrics", () => {
  it.each([
    ["/metrics", rootPath],
    ["/api/v1/metrics (getMetrics)", apiPath],
  ])("answers %s 404 NOT_FOUND, as the contract declares [TFX-09]", async (_path, get) => {
    const response = get();
    expect(response.status).toBe(404);
    expect(response.headers.get("content-type")).toBe("application/problem+json");
    expect(await response.json()).toEqual({ code: "NOT_FOUND", status: 404 });
  });
});
