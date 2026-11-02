// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeClient, fakeClient } from "@/test/fixtures";
import { PREFERENCES } from "@/test/grid-preferences";

import { KeptWorkload } from "./kept-workload";

// The server of Next, as far as the recording needs it: the fake back, and the address shown.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useSearchParams: () => new URLSearchParams(page.search),
}));

/** The bodies the fake back received to record preferences. */
function writes() {
  return (server.client as FakeClient).calls.filter(({ route }) => route === PREFERENCES);
}

/** Show the workload at the address given, with what the account kept. */
function show(filters?: Record<string, string>) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <KeptWorkload preferences={filters === undefined ? undefined : { filters }} />
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
});

afterEach(() => {
  page.search = "";
});

describe("the settings the aggregated workload records", () => {
  it("records the horizon, the threshold and the node the address shows, under the key of the screen, and nothing of the rest of the perimeter [WF-PTF-0060-A]", async () => {
    page.search = "horizon_months=24&under_load_threshold=0.3&org_node_id=n1&states=completed";
    show();
    await waitFor(() => {
      expect(writes()).toHaveLength(1);
    });
    expect(writes()[0]?.body).toEqual({
      grids: {
        portfolio_workload: {
          filters: { horizon_months: "24", under_load_threshold: "0.3", org_node_id: "n1" },
        },
      },
    });
  });

  it("records nothing when the address shows what the account kept [WF-PTF-0060-A]", async () => {
    page.search = "horizon_months=12&states=completed";
    show({ horizon_months: "12" });
    await new Promise((done) => setTimeout(done, 50));
    expect(writes()).toEqual([]);
  });

  it("records the settings lifted when the default is chosen [WF-PTF-0060-A]", async () => {
    page.search = "horizon_months=";
    show({ horizon_months: "12" });
    await waitFor(() => {
      expect(writes()).toHaveLength(1);
    });
    expect(writes()[0]?.body).toEqual({ grids: { portfolio_workload: { filters: {} } } });
  });

  it("records the node of an address restored, with the horizon and the threshold kept [WF-PTF-0060-A]", async () => {
    page.search = "org_node_id=n2&horizon_months=12&under_load_threshold=0.5";
    show({ horizon_months: "12", under_load_threshold: "0.5", org_node_id: "n1" });
    await waitFor(() => {
      expect(writes()).toHaveLength(1);
    });
    expect(writes()[0]?.body).toEqual({
      grids: {
        portfolio_workload: {
          filters: { horizon_months: "12", under_load_threshold: "0.5", org_node_id: "n2" },
        },
      },
    });
  });
});
