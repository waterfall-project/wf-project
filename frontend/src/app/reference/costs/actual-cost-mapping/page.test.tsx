// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import ActualCostMappingPage from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/reference/costs/actual-cost-mapping",
  useSearchParams: () => new URLSearchParams(),
}));

/** Render the page in French. */
async function rendered(): Promise<string> {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {(await ActualCostMappingPage()) as ReactNode}
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  server.answers = { "GET /me": "me", "GET /reference/actual-cost-mapping": "actual_cost_mapping" };
});

describe("the page of the correspondence of the actual costs", () => {
  it("offers the form to a session that holds cost_settings.write, saying the fake back keeps nothing [WF-REF-0190-A]", async () => {
    const page = await rendered();
    expect(page).toContain("Correspondance des coûts réels");
    expect(page).toContain('aria-label="Correspondance de l’extraction des coûts réels"');
    expect(page).toContain("Enregistrer la correspondance");
    expect(page).toMatch(/role="note"/);
  });

  it("shows the lists with no command to a session that only holds cost_settings.read [WF-REF-0190-A]", async () => {
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    const page = await rendered();
    expect(page).toContain("Nº pièce référence");
    expect(page).toContain("Texte de commande");
    expect(page).not.toContain("Enregistrer la correspondance");
    expect(page).not.toContain("<input");
    expect(page).not.toMatch(/role="note"/);
  });

  it("says the four columns without a label of an empty correspondence [WF-REF-0190-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/actual-cost-mapping": "actual_cost_mapping_empty",
    };
    expect(await rendered()).toContain("Colonnes exigées sans intitulé");
  });
});
