// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SignedOut } from "@/api/problem";
import { SESSION_REQUIRED_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import AvatarPage, { generateMetadata as avatarMetadata } from "./avatar/page";
import AccountPage, { generateMetadata as accountMetadata } from "./page";
import PasswordPage, { generateMetadata as passwordMetadata } from "./password/page";

const server = vi.hoisted((): { answers: FakeAnswers; clients: FakeClient[] } => ({
  answers: {},
  clients: [],
}));

vi.mock("@/api/server", () => ({
  serverClient: () => {
    const client = fakeClient(server.answers);
    server.clients.push(client);
    return client;
  },
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const AVATAR = "GET /users/{user_id}/avatar";
// The eight bytes that open every PNG file, standing for an image.
const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

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

/** The routes the pages called, in order. */
function routes(): string[] {
  return server.clients.flatMap((client) => client.calls.map((call) => call.path));
}

/** The value chosen in each choice of a page — the language, then the mode —, as Radix marks it. */
function choices(markup: string): (string | undefined)[] {
  return markup
    .split('role="radiogroup"')
    .slice(1)
    .map((group) => {
      const radios = group.match(/<button[^>]*role="radio"[^>]*>/g) ?? [];
      const checked = radios.find((radio) => radio.includes('aria-checked="true"'));
      return checked === undefined ? undefined : /value="([^"]*)"/.exec(checked)?.[1];
    });
}

beforeEach(() => {
  server.answers = { "GET /me": "me", "GET /session": "session" };
  server.clients = [];
});

describe("the screen of the account", () => {
  it("says what the account is, and offers its preferences as the account holds them", async () => {
    const page = html(await AccountPage());
    expect(text(page)).toContain(
      "Informations du compte Nom Camille Martin Adresse électronique camille.martin@example.com Origine du compte Créé dans Waterfall",
    );
    expect(text(page)).toContain("Préférences d’affichage");
    expect(choices(page)).toEqual(["default", "default"]);
    expect(page).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Mon compte<\/h1>/);
    expect([...page.matchAll(/<a [^>]*href="([^"]*)"/g)].map(([, href]) => href)).toEqual([
      "/account/password",
      "/account/avatar",
    ]);
    expect(routes()).toEqual(["/me"]);
    expect(await accountMetadata()).toEqual({ title: "Mon compte — Waterfall" });
  });

  it("offers the preferences the account chose", async () => {
    server.answers = { ...server.answers, "GET /me": "me_english" };
    const page = html(await AccountPage());
    expect(choices(page)).toEqual(["en", "default"]);
  });

  it("leads to the sign-in page when the session is gone", async () => {
    server.answers = { "GET /me": { problem: { code: "SESSION_EXPIRED", status: 401 } } };
    const failure = AccountPage();
    await expect(failure).rejects.toBeInstanceOf(SignedOut);
    await expect(failure).rejects.toMatchObject({ digest: SESSION_REQUIRED_DIGEST });
  });
});

describe("the change of the password", () => {
  it("offers a local account its current and its new password", async () => {
    const page = html(await PasswordPage());
    expect(page).toMatch(/autoComplete="current-password"/i);
    expect(page).toMatch(/autoComplete="new-password"/i);
    expect(text(page)).toContain("Changer le mot de passe");
    expect(await passwordMetadata()).toEqual({ title: "Changer le mot de passe — Waterfall" });
  });

  it("offers no form to an account of the directory, whose password the API would not change, and says where it is changed", async () => {
    server.answers = { ...server.answers, "GET /me": "me_directory" };
    const page = html(await PasswordPage());
    expect(page).not.toMatch(/type="password"/);
    expect(text(page)).toContain(
      "Votre mot de passe est celui de l’annuaire ou du fournisseur d’identité dont vient votre compte : il ne se change pas dans Waterfall.",
    );
  });
});

describe("the avatar of the account", () => {
  it("shows the image the account has, written into the page by the server", async () => {
    server.answers = {
      ...server.answers,
      "GET /me": "me_with_avatar",
      [AVATAR]: { body: new Blob([PNG], { type: "image/png" }), type: "image/png", status: 200 },
    };
    const screen = await AvatarPage();
    const page = html(screen);
    // The image, loaded by the browser from the page itself (AvatarImage); the initials until then.
    const source = `data:image/png;base64,${Buffer.from(PNG).toString("base64")}`;
    expect(screen.props).toMatchObject({ source });
    expect(text(page)).toContain("CM");
    expect(routes()).toEqual(["/me", "/users/01926f3a-7c00-7000-8000-000000000301/avatar"]);
    expect(text(page)).toContain("Retirer l’avatar");
    expect(await avatarMetadata()).toEqual({ title: "Changer l’avatar — Waterfall" });
  });

  it("shows the initials of an account without an image, reads none, and offers nothing to withdraw", async () => {
    const page = html(await AvatarPage());
    expect(page).not.toMatch(/<img/);
    expect(text(page)).toContain("CM Aucune image : vos initiales en tiennent lieu.");
    expect(text(page)).not.toContain("Retirer l’avatar");
    expect(routes()).toEqual(["/me"]);
    expect(page).toMatch(/<input[^>]*type="file"[^>]*accept="image\/png,image\/jpeg"/);
  });

  it("shows the initials when the image cannot be read", async () => {
    server.answers = {
      ...server.answers,
      "GET /me": "me_with_avatar",
      [AVATAR]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    const page = html(await AvatarPage());
    expect(page).not.toMatch(/<img/);
    expect(text(page)).toContain("CM Aucune image");
  });
});
