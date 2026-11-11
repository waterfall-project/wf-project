// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { updateGridPreferences } from "@/api/actions/preferences";
import { fakeClient } from "@/test/fixtures";

import { useKeptWriter } from "./settings";

// The server of Next as far as the action needs it: the API out of reach for the first call
// (the fetch rejects), the fake back behind serverClient for the next ones.
const server = vi.hoisted(() => ({ attempts: 0 }));
vi.mock("@/api/server", () => ({
  serverClient: () => {
    server.attempts += 1;
    if (server.attempts === 1) {
      throw new TypeError("fetch failed");
    }
    return fakeClient({ "PATCH /me/preferences": "preferences" });
  },
}));
vi.mock("next/cache", () => ({ refresh: () => undefined }));

describe("the writer of the preferences a grid or a chart keeps", () => {
  it("says the API out of reach when the server action rejects, and writes again after [WF-ADM-0040-A]", async () => {
    const { result } = renderHook(() =>
      useKeptWriter<{ readonly hidden_columns: string[] }>("estimate", updateGridPreferences),
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
    expect(server.attempts).toBe(2);
  });
});
