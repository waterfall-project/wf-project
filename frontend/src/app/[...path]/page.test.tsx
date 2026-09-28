// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import ScreenPage, { generateMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;

/** The parameters of the page for an address. */
function at(address: string) {
  return { params: Promise.resolve({ path: address.split("/").slice(1) }) };
}

/** Render a page in French, as the shell hands it its texts. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {page}
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  server.answers = { "GET /me": "me", "GET /projects/{project_id}": "project" };
});

describe("the page of a function still to come", () => {
  it.each([
    ["/portfolio/projects", "Portefeuille de projets"],
    ["/reference/costs", "Paramètres de coûts"],
    ["/admin/users", "Gestion des utilisateurs"],
    ["/system", "Surveillance de l’état du système"],
  ])(
    "exists at %s without any project open, and names its function [WF-IHM-0010-A]",
    async (address, name) => {
      expect(html(await ScreenPage(at(address)))).toBe(
        `<main class="space-y-2 p-6"><h1 class="text-2xl font-semibold">${name}</h1>` +
          '<p class="text-muted-foreground">Cet écran est à venir.</p></main>',
      );
      expect((await generateMetadata(at(address))).title).toBe(`${name} — Waterfall`);
    },
  );

  it("exists in the revision of a project, whose tab names the function and the project", async () => {
    const address = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
    expect(html(await ScreenPage(at(address)))).toContain(
      '<h1 class="text-2xl font-semibold">Estimation du reste à engager</h1>',
    );
    expect((await generateMetadata(at(address))).title).toBe(
      "Estimation du reste à engager · Modernisation du poste de commande — Waterfall",
    );
  });

  it("names the function alone when the project cannot be read", async () => {
    server.answers = { "GET /me": "me", "GET /projects/{project_id}": NOT_FOUND };
    const address = `/projects/${PROJECT}/revisions/${REVISION}/planning`;
    expect((await generateMetadata(at(address))).title).toBe("Planification — Waterfall");
  });

  it("is not found at an address that leads to no function", async () => {
    await expect(ScreenPage(at("/admin/nobody"))).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
    expect(await generateMetadata(at("/admin/nobody"))).toEqual({});
  });
});
