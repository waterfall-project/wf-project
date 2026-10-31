// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { Project } from "@/components/context/reading";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";

import { ImportReport } from "./import-report";
import { importOffers } from "./offers";

// The server of Next, as far as the report needs it: the fake back behind serverClient, which the
// report asks nothing of while it is only read.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => `/projects/${PROJECT}/revisions/${REVISION}/exchanges`,
  useSearchParams: () => new URLSearchParams(),
}));

type Import = components["schemas"]["Import"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const START = `/projects/${PROJECT}/revisions/${REVISION}/exchanges?as_of=2026-05-31`;

/** Render the report of an import of the contract, as the screen shows it, in French. */
function open(entry: Import) {
  server.client = fakeClient({});
  const offers = importOffers(example("project") as Project);
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <ImportReport projectId={PROJECT} entry={entry} offer={offers[entry.kind]} start={START} />
    </NextIntlClientProvider>,
  );
}

describe("the report of an import, what the file dates otherwise", () => {
  it("names each task the file dates otherwise than Waterfall computes it, with the columns that differ, as information and not a reason to confirm", () => {
    open(example("import_planning_mismatch") as Import);
    const table = screen.getByRole("table", { name: "Tâches datées autrement par le fichier" });
    expect(
      within(table)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual(["TâcheChamps", "ÉtudesFin", "Revue de conceptionFin"]);
    expect(screen.getByText(/^2 tâches datées autrement par le fichier/)).toBeVisible();
  });

  it("names no such task for a file Waterfall dates alike, an estimate", () => {
    open(example("import_analysed") as Import);
    expect(
      screen.queryByRole("table", { name: "Tâches datées autrement par le fichier" }),
    ).toBeNull();
  });
});
