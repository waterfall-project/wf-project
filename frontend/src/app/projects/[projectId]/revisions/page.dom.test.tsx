// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of the revisions, rendered in a document (US-2130): a screen of consultation in the
 * airy column, a card per section it has — the history, the comparison, the structures, the rate
 * update —, « Ouvrir une révision en cours » the one filled command, the principal one of the card
 * of the history; the structure of the screen is as it was (decision of the author of 2026-11-14,
 * EP-27 recasts it), the commands of the revision at the right of the title, outlined. The rule of
 * the commands is that of `expectCommandRule`.
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SCREEN } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectCommandRule } from "@/test/command-rule";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import RevisionsPage from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects/p/revisions",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const DRAFT = "01926f3a-7c00-7000-8000-000000000102";

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1400);
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project_without_current_revision",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    "GET /projects/{project_id}/revisions/{revision_id}/rate-update": "rate_update",
    "GET /projects/{project_id}/revisions/comparison": "comparison",
  };
});

/** Render the screen of the revisions at an address, in French. */
async function renderRevisions(search: Record<string, string> = {}) {
  const page = await RevisionsPage({
    params: Promise.resolve({ projectId: PROJECT }),
    searchParams: Promise.resolve(search),
  });
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {page}
    </NextIntlClientProvider>,
  );
}

describe("the screen of the revisions, rendered", () => {
  it("sets each section in a card, « Ouvrir une révision en cours » filled in the card of the history, the one filled command of the screen [WF-IHM-0090-A]", async () => {
    const { container } = await renderRevisions();
    expect(screen.getByRole("main")).toHaveClass(...SCREEN.airy.split(" "));
    for (const title of ["Historique des révisions", "Comparaison de deux révisions"]) {
      expect(screen.getByRole("region", { name: title })).toHaveAttribute(
        "data-slot",
        "section-card",
      );
    }
    const history = screen.getByRole("region", { name: "Historique des révisions" });
    const open = within(history).getByRole("button", { name: "Ouvrir une révision en cours" });
    expect(open).toHaveClass(...buttonVariants({ variant: "default", size: "sm" }).split(" "));
    expect(open.closest('[data-slot="section-card-principal"]')).toHaveAttribute(
      "data-does",
      "create",
    );
    expect(container.querySelectorAll("button.bg-primary, a.bg-primary")).toHaveLength(1);
    expectCommandRule(container);
  });

  it("keeps the commands of the revision it reads in at the right of the title, outlined, and the structures and the rate update in their cards [WF-IHM-0090-A]", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project" };
    const { container } = await renderRevisions({ revision_id: DRAFT });
    const header = container.querySelector('[data-slot="screen-commands"]');
    expect(header).not.toBeNull();
    expect(
      within(header as HTMLElement).getByRole("button", { name: "Marquer la révision" }),
    ).toHaveClass(...buttonVariants({ variant: "outline", size: "sm" }).split(" "));
    for (const title of ["Structures de coûts", "Mise à jour des taux proposée"]) {
      expect(screen.getByRole("region", { name: title })).toHaveAttribute(
        "data-slot",
        "section-card",
      );
    }
    expectCommandRule(container);
  });
});
