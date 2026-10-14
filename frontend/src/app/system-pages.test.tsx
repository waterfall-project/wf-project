// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { UNREACHABLE_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import GlobalError from "./global-error";
import NotFound from "./not-found";

const server = vi.hoisted(() => ({ client: undefined as FakeClient | undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// The address shown, a screen with its query, which the sign-in comes back to.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams("states=active"),
}));

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** The screen not found, for a request whose session the API reads as it answers `getMe`. */
async function notFound(me: NonNullable<FakeAnswers["GET /me"]>): Promise<string> {
  server.client = fakeClient({ "GET /me": me });
  const screen = await NotFound();
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {screen}
    </NextIntlClientProvider>,
  );
}

describe("the screen not found", () => {
  it("says the address leads to nothing the user may consult, whether it exists or not, and leads home", async () => {
    const html = await notFound("me");
    expect(text(html)).toBe(
      "Introuvable Cette adresse ne mène à rien que vous puissiez consulter. Retour à l’accueil",
    );
    expect(html).toMatch(
      /^<main[^>]*>.*<h1[^>]*><svg[^>]*aria-hidden="true".*<\/svg>Introuvable<\/h1>/,
    );
    expect(html).toMatch(/<a class="[^"]*" href="\/"><svg[^>]*aria-hidden="true"/);
  });

  it("says the same when the session cannot be read, the API out of reach: nothing to sign in to", async () => {
    const html = await notFound({ problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } });
    expect(text(html)).toBe(
      "Introuvable Cette adresse ne mène à rien que vous puissiez consulter. Retour à l’accueil",
    );
  });

  it("without a session, asks for one and offers the sign-in page, which comes back to the address shown, the home included — never « not found » (#1000) [WF-SEC-0020-A]", async () => {
    const html = await notFound({ problem: { code: "SESSION_REQUIRED", status: 401 } });
    expect(text(html)).toBe(
      "Session requise L’écran demande une session ouverte : connectez-vous, vous y reviendrez ensuite. " +
        "Se connecter",
    );
    expect(html).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true".*<\/svg>Session requise<\/h1>/);
    expect(html).toContain(`href="/login?next=${encodeURIComponent("/?states=active")}"`);
    expect(html).not.toContain("Retour à l’accueil");
  });

  it("does not ask an account the API refuses to sign in, which would loop: it is not found", async () => {
    const html = await notFound({ problem: { code: "ACCOUNT_DEACTIVATED", status: 401 } });
    expect(text(html)).toContain("Introuvable");
    expect(html).not.toContain("/login");
  });
});

describe("the screen of failure of the root layout", () => {
  it("is a document of its own, in the reference language on the server, never a blank page", () => {
    const error = Object.assign(new Error("An error occurred."), { digest: UNREACHABLE_DIGEST });
    const html = renderToStaticMarkup(<GlobalError error={error} retry={vi.fn()} />);
    expect(html).toMatch(
      /^<html lang="fr" class="font-geist-sans"><head><title>Waterfall<\/title>/,
    );
    expect(text(html)).toBe(
      "Waterfall Service injoignable " +
        "Le service ne répond pas : l’écran n’a pas pu lire ses données. " +
        "Réessayez dans un instant. Réessayer",
    );
  });
});
