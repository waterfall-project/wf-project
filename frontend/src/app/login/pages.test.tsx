// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UnexpectedAnswer } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import LoginPage, { generateMetadata as loginMetadata } from "./page";
import PasswordResetPage, { generateMetadata as resetMetadata } from "./reset/page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

/** Render a page in French, as the shell hands it its texts. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {page}
    </NextIntlClientProvider>,
  );
}

/** What a page says, its tags left out, every space — a no-break one included — a plain one. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** The search parameters of a page. */
function search(parameters: Record<string, string> = {}) {
  return { searchParams: Promise.resolve(parameters) };
}

/** The links of a page, each as its address and its text. */
function links(markup: string): [string, string][] {
  return [...markup.matchAll(/<a [^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/g)].map(([, href, inner]) => [
    href ?? "",
    text(inner ?? ""),
  ]);
}

beforeEach(() => {
  server.answers = {
    "GET /session": "session",
    "GET /session/providers": "auth_providers",
  };
});

describe("the sign-in page", () => {
  it("offers the local accounts, those of the directory and the identity provider the installation enables, and the password forgotten", async () => {
    const page = html(await LoginPage(search()));

    expect(page).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"/);
    expect(text(page)).toContain(
      "Connexion Avec votre compte Waterfall ou celui de l’annuaire « Annuaire Exemple ».",
    );
    expect(page).toMatch(/<label[^>]*>Adresse électronique<\/label><input[^>]*type="email"/);
    expect(page).toMatch(/<label[^>]*>Mot de passe<\/label><input[^>]*type="password"/);
    expect(links(page)).toEqual([
      ["/api/v1/session/oidc/start", "Se connecter avec Exemple SSO"],
      ["/login/reset", "Mot de passe oublié ?"],
    ]);
    expect(await loginMetadata()).toEqual({ title: "Connexion — Waterfall" });
  });

  it("offers the local accounts alone when the installation enables neither the directory nor the identity provider", async () => {
    server.answers = { ...server.answers, "GET /session/providers": "auth_providers_local" };
    const page = html(await LoginPage(search()));
    expect(text(page)).toContain("Connexion Avec votre compte Waterfall.");
    expect(text(page)).not.toContain("annuaire");
    expect(links(page)).toEqual([["/login/reset", "Mot de passe oublié ?"]]);
    expect(page).toMatch(/type="password"/);
  });

  it("copies no rule of the password into its fields: the API judges what is typed", async () => {
    const page = html(await LoginPage(search()));
    for (const input of page.match(/<input[^>]*>/g) ?? []) {
      expect(input).not.toMatch(/minLength|maxLength|pattern/i);
    }
  });

  it("says a failure of the API to list the providers, rather than a page without them", async () => {
    server.answers = {
      ...server.answers,
      "GET /session/providers": { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } },
    };
    await expect(LoginPage(search())).rejects.toBeInstanceOf(UnexpectedAnswer);
  });
});

describe("the password forgotten", () => {
  it("asks first for the address of the account, to which the API sends a link", async () => {
    const page = html(await PasswordResetPage(search()));
    expect(text(page)).toContain(
      "Mot de passe oublié Indiquez l’adresse électronique de votre compte : un lien pour choisir un nouveau mot de passe lui sera envoyé.",
    );
    expect(page).toMatch(/<input[^>]*type="email"/);
    expect(page).not.toMatch(/type="password"/);
    expect(links(page)).toEqual([["/login", "Retour à la connexion"]]);
    expect(await resetMetadata()).toEqual({ title: "Mot de passe oublié — Waterfall" });
  });

  it("asks then, from the link and its token, for the new password", async () => {
    const page = html(await PasswordResetPage(search({ token: "a-token-of-twenty-characters" })));
    expect(text(page)).toContain(
      "Nouveau mot de passe Choisissez le nouveau mot de passe de votre compte.",
    );
    expect(page).toMatch(/<input[^>]*type="password"[^>]*autoComplete="new-password"/i);
    expect(page).not.toMatch(/type="email"/);
  });

  it("takes an empty token for none", async () => {
    const page = html(await PasswordResetPage(search({ token: "" })));
    expect(page).toMatch(/type="email"/);
  });
});
