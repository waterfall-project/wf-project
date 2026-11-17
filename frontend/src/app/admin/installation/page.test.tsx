// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of the installation (FBS-1.6, EP-25 US-2120/L2), rendered by the server against the
 * fake back: the card « Installation » with the name of the company and, read only, the currency,
 * the default language and the time zone; its command only under `installation.write`; the screen
 * not found without `installation.read`.
 */
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import InstallationPage, { generateMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/admin/installation",
  useSearchParams: () => new URLSearchParams(),
}));
// The session of the contract, some of its permissions withdrawn for a test.
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
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

/** Render the screen in French. */
function rendered(page: unknown): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  withdrawn.permissions = [];
  server.answers = {
    "GET /me": "me",
    "GET /installation": "installation",
    "GET /reference/settings": "reference_settings",
  };
});

describe("the installation", () => {
  it("titles the tab with the function", async () => {
    expect((await generateMetadata()).title).toBe("Installation — Waterfall");
  });

  it("shows a card « Installation » with the name of the company, and the currency, the default language and the time zone read only", async () => {
    const page = rendered(await InstallationPage());
    expect(page).toMatch(/<section[^>]*aria-label="Installation"/);
    expect(page).toMatch(/<dt[^>]*>Nom de l’entreprise<\/dt><dd[^>]*>Delmas Automatismes/);
    expect(page).toMatch(/<dt[^>]*>Devise<\/dt><dd[^>]*>EUR/);
    expect(page).toMatch(/<dt[^>]*>Langue par défaut<\/dt><dd[^>]*>Français/);
    expect(page).toMatch(/<dt[^>]*>Fuseau horaire<\/dt><dd[^>]*>Europe\/Paris/);
    expect(page).toContain("Modifier le nom de l’entreprise");
  });

  it("offers the command that modifies the name only under installation.write", async () => {
    withdrawn.permissions = ["installation.write"];
    const page = rendered(await InstallationPage());
    expect(page).toContain("Delmas Automatismes");
    expect(page).not.toContain("Modifier le nom de l’entreprise");
  });

  it("is not found by a session without installation.read, as an address that leads nowhere", async () => {
    withdrawn.permissions = ["installation.read", "installation.write"];
    await expect(InstallationPage()).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });
});
