// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import * as apiPath from "@/app/api/v1/metrics/route";
import * as rootPath from "@/app/metrics/route";

const METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] as const;

describe("the public door at the point of metrics", () => {
  describe.each([
    ["/metrics", rootPath],
    ["/api/v1/metrics (getMetrics)", apiPath],
  ])("%s", (_path, route) => {
    it.each(METHODS)(
      "answers %s 404 NOT_FOUND, as the contract declares, not the 405 of Next [TFX-09]",
      async (method) => {
        const response = route[method]();
        expect(response.status).toBe(404);
        expect(response.headers.get("content-type")).toBe("application/problem+json");
        expect(await response.json()).toEqual({ code: "NOT_FOUND", status: 404 });
      },
    );
  });
});
