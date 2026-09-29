// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { fakeClient } from "@/test/fixtures";

import AccountPageToCome, { generateMetadata } from "./page";

vi.mock("@/api/server", () => ({
  serverClient: () => fakeClient({ "GET /session": "session" }),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

/** The parameters of the page for the segments after `/account`. */
function at(...section: string[]) {
  return { params: Promise.resolve(section.length === 0 ? {} : { section }) };
}

/** Render a page in French, as the shell hands it its texts. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {page}
    </NextIntlClientProvider>,
  );
}

/** What a page says, its tags left out. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

describe("the pages of the account still to come", () => {
  it.each([
    [[], "Mon compte"],
    [["password"], "Changer le mot de passe"],
    [["avatar"], "Changer l’avatar"],
  ])("exist under /account/%s, each naming its page and its icon", async (section, name) => {
    const page = html(await AccountPageToCome(at(...section)));
    expect(text(page)).toBe(`${name} Cet écran est à venir.`);
    expect(page).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"/);
    expect((await generateMetadata(at(...section))).title).toBe(`${name} — Waterfall`);
  });

  it("is not found at an address under /account that leads to no page of the account", async () => {
    await expect(AccountPageToCome(at("nobody"))).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
    expect(await generateMetadata(at("password", "more"))).toEqual({});
  });
});
