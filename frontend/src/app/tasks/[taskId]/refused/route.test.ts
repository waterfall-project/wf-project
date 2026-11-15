// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { GET } from "./route";

describe("the page a hidden frame is sent to when the result is refused", () => {
  it("is an empty document, never kept, whatever the refusal its address says (#3297) [WF-DAT-0120-A]", async () => {
    const response = GET();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("text/html; charset=utf-8");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    // Nothing of the application: no script, no body.
    const html = await response.text();
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<body");
  });
});
