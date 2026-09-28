// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("HomePage", () => {
  it("names the product", () => {
    expect(renderToStaticMarkup(<HomePage />)).toContain("<h1>Waterfall</h1>");
  });
});
