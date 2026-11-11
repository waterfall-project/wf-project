// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useKeptWriter } from "./settings";

describe("the writer of the preferences a grid or a chart keeps", () => {
  it("says the API out of reach when the server action rejects, and writes again after [WF-ADM-0040-A]", async () => {
    let attempts = 0;
    const { result } = renderHook(() =>
      useKeptWriter<{ readonly hidden_columns: string[] }>("estimate", () => {
        attempts += 1;
        return attempts === 1
          ? Promise.reject(new TypeError("fetch failed"))
          : Promise.resolve({ kind: "done", data: null });
      }),
    );

    act(() => {
      result.current.writeNow({ hidden_columns: [] });
    });
    await waitFor(() => {
      expect(result.current.outcome).toEqual({ kind: "unreachable" });
    });

    act(() => {
      result.current.writeNow({ hidden_columns: ["cost"] });
    });
    await waitFor(() => {
      expect(result.current.outcome).toBeUndefined();
    });
    expect(attempts).toBe(2);
  });
});
