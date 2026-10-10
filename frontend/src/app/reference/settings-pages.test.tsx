// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import IndicatorSettingsPage from "./indicators/page";
import RiskSettingsPage from "./risks/page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
// The session of the contract, one of its permissions withdrawn for a test: no account of the witness
// writes the settings of one of the two screens without the other (decision of the author, 2026-10-09).
const withdrawn = vi.hoisted(() => ({ permissions: [] as string[] }));
vi.mock("@/session/request", async (original) => {
  const actual = await original<typeof import("@/session/request")>();
  return {
    ...actual,
    requestSession: async () => {
      const session = await actual.requestSession();
      return session === undefined
        ? undefined
        : {
            ...session,
            permissions: session.permissions.filter(
              (permission) => !withdrawn.permissions.includes(permission),
            ),
          };
    },
  };
});
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/reference/risks",
  useSearchParams: () => new URLSearchParams(),
}));

/** Render a page of the reference data in French. */
function rendered(page: unknown): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** Serve the settings of the witness to a session, by the name of its example. */
function servedTo(session: "session" | "session_manager") {
  server.answers = { "GET /session": session, "GET /reference/settings": "reference_settings" };
}

/** The note that says the fake back keeps nothing. */
const MOCKUP = /role="note"[^>]*>.*?le service simulé répond/;

beforeEach(() => {
  servedTo("session");
  withdrawn.permissions = [];
});

describe("the forms of the settings of the risks and of the indicators", () => {
  it("offer the modification of the risk matrix to a session that may modify the risk settings, saying the fake back keeps nothing, beside the matrix it shows [WF-IHM-0090-A]", async () => {
    const page = rendered(await RiskSettingsPage());
    expect(page).toContain("Modifier la matrice de risques");
    expect(page).toMatch(MOCKUP);
    expect(page).toContain('aria-label="Bornes de la matrice de risques"');
    expect(page).toContain('aria-label="Zones de la matrice de risques"');
    // The form of the other screen is not offered here.
    expect(page).not.toContain("Modifier les seuils et le délai");
  });

  it("offer the modification of the thresholds and the delay to a session that may modify the indicator settings, saying the fake back keeps nothing [WF-IHM-0090-A]", async () => {
    const page = rendered(await IndicatorSettingsPage());
    expect(page).toContain("Modifier les seuils et le délai");
    expect(page).toMatch(MOCKUP);
    expect(page).toContain('aria-label="Seuils d’alerte des indices"');
    expect(page).not.toContain("Modifier la matrice de risques");
  });

  it("offer the form of the risks alone to a session that may modify the risk settings but not the indicator settings [WF-IHM-0090-A]", async () => {
    withdrawn.permissions = ["indicator_settings.write"];
    const risks = rendered(await RiskSettingsPage());
    const indicators = rendered(await IndicatorSettingsPage());
    expect(risks).toContain("Modifier la matrice de risques");
    expect(risks).toMatch(MOCKUP);
    expect(indicators).not.toContain("Modifier les seuils et le délai");
    expect(indicators).not.toMatch(MOCKUP);
    expect(indicators).toContain("8 semaines");
  });

  it("offer the form of the indicators alone to a session that may modify the indicator settings but not the risk settings [WF-IHM-0090-A]", async () => {
    withdrawn.permissions = ["risk_settings.write"];
    const risks = rendered(await RiskSettingsPage());
    const indicators = rendered(await IndicatorSettingsPage());
    expect(indicators).toContain("Modifier les seuils et le délai");
    expect(indicators).toMatch(MOCKUP);
    expect(risks).not.toContain("Modifier la matrice de risques");
    expect(risks).not.toMatch(MOCKUP);
    expect(risks).toContain('aria-label="Zones de la matrice de risques"');
  });

  it("offer neither form to a session that may only read the settings, nor say anything of the fake back [WF-IHM-0090-A]", async () => {
    servedTo("session_manager");
    const risks = rendered(await RiskSettingsPage());
    const indicators = rendered(await IndicatorSettingsPage());
    expect(risks).not.toContain("Modifier la matrice de risques");
    expect(indicators).not.toContain("Modifier les seuils et le délai");
    for (const page of [risks, indicators]) {
      expect(page).not.toMatch(MOCKUP);
    }
    // The settings are shown all the same.
    expect(risks).toContain('aria-label="Zones de la matrice de risques"');
    expect(indicators).toContain("8 semaines");
  });
});
