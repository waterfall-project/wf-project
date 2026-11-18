// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of the revisions, rendered in a document (US-2130): a screen of consultation in the
 * airy column, one card — the history (US-2370) —, « Ouvrir une révision en cours » the one filled
 * command, the principal one of the card of the history, the commands of the revision at the right
 * of the title, outlined. « Comparer à la révision lue » leads each marked revision, but the one
 * read, to the grids the session may read, that revision as their base. The rule of the commands is
 * that of `expectCommandRule`.
 */
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RevisionHistory } from "@/components/revisions/revision-history";
import { SCREEN } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectCommandRule } from "@/test/command-rule";
import type { ProjectContext } from "@/navigation/context";
import { example, type FakeAnswers, fakeClient } from "@/test/fixtures";

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
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1400);
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project_without_current_revision",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
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
  it("sets the history alone in a card, « Ouvrir une révision en cours » filled in the card of the history, the one filled command of the screen [WF-IHM-0090-A]", async () => {
    const { container } = await renderRevisions();
    expect(screen.getByRole("main")).toHaveClass(...SCREEN.airy.split(" "));
    expect(screen.getByRole("region", { name: "Historique des révisions" })).toHaveAttribute(
      "data-slot",
      "section-card",
    );
    expect(container.querySelectorAll('[data-slot="section-card"]')).toHaveLength(1);
    expect(screen.queryByRole("region", { name: "Comparaison de deux révisions" })).toBeNull();
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

  it("keeps the commands of the revision it reads in at the right of the title, outlined, the rate update among them, and no card of the structures nor of the rate update [WF-IHM-0090-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project",
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_rate_update_offered",
    };
    const { container } = await renderRevisions({ revision_id: DRAFT });
    const header = container.querySelector('[data-slot="screen-commands"]');
    expect(header).not.toBeNull();
    expect(
      within(header as HTMLElement).getByRole("button", { name: "Marquer la révision" }),
    ).toHaveClass(...buttonVariants({ variant: "outline", size: "sm" }).split(" "));
    expect(
      within(header as HTMLElement).getByRole("button", {
        name: "Appliquer la mise à jour des taux",
      }),
    ).toHaveClass(...buttonVariants({ variant: "outline", size: "sm" }).split(" "));
    for (const title of [
      "Structures de coûts",
      "Mise à jour des taux proposée",
      "Désignation de la référence",
    ]) {
      expect(screen.queryByRole("region", { name: title })).toBeNull();
    }
    expectCommandRule(container);
  });

  it("sets the report of the import its address names in a card of a section, above the history, as the screen of the imports and exports does [WF-IHM-0100-A] #3410", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/imports/{import_id}": "import_analysed",
    };
    const { container } = await renderRevisions({ import: IMPORT });
    const report = screen.getByRole("region", { name: /^Compte rendu de l’import/ });
    expect(report).toHaveAttribute("data-slot", "section-card");
    expect(report.className).not.toContain("rounded-md border p-3");
    const history = screen.getByRole("region", { name: "Historique des révisions" });
    expect(report.compareDocumentPosition(history) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expectCommandRule(container);
  });
});

describe("« Comparer à la révision lue » in the history [WF-IHM-0010-A] US-2370", () => {
  const CONTEXT: ProjectContext = {
    projectId: PROJECT,
    revisionId: DRAFT,
    revisionInPath: false,
    parameters: new URLSearchParams(),
  };
  const REVISIONS = example("revisions") as {
    items: Parameters<typeof RevisionHistory>[0]["revisions"];
  };

  function history(
    permissions: readonly ("planning.read" | "estimate.read" | "remaining.read")[],
    context = CONTEXT,
  ) {
    return render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <RevisionHistory
          revisions={REVISIONS.items}
          context={context}
          projectLockVersion={1}
          permissions={permissions}
        />
      </NextIntlClientProvider>,
    );
  }

  it("offers the planning, the estimate and the remaining to commit on each marked revision but the one read, each at the address of the revision read, that revision as the base", async () => {
    history(["planning.read", "estimate.read", "remaining.read"]);
    const commands = screen.getAllByRole("button", { name: /^Comparer à la révision lue/ });
    expect(commands).toHaveLength(2);
    await userEvent.click(
      screen.getByRole("button", {
        name: "Comparer à la révision lue\u00a0: «\u00a0Offre v1.0\u00a0»",
      }),
    );
    const menu = screen.getAllByRole("menuitem");
    expect(menu.map((item) => item.getAttribute("href"))).toEqual([
      `/projects/${PROJECT}/revisions/${DRAFT}/planning?base_revision_id=${OFFER}`,
      `/projects/${PROJECT}/revisions/${DRAFT}/estimate?base_revision_id=${OFFER}`,
      `/projects/${PROJECT}/revisions/${DRAFT}/remaining?base_revision_id=${OFFER}`,
    ]);
  });

  it("offers the grids the session may read alone, and nothing to a session that may read none", async () => {
    const { unmount } = history(["estimate.read"]);
    expect(screen.getAllByRole("button", { name: /^Comparer à la révision lue/ })).toHaveLength(2);
    await userEvent.click(
      screen.getByRole("button", {
        name: "Comparer à la révision lue\u00a0: «\u00a0Offre v1.0\u00a0»",
      }),
    );
    const items = screen.getAllByRole("menuitem");
    expect(items).toHaveLength(1);
    expect(items[0]).toHaveTextContent("Chiffrage et devis");
    expect(items[0]?.getAttribute("href")).toBe(
      `/projects/${PROJECT}/revisions/${DRAFT}/estimate?base_revision_id=${OFFER}`,
    );
    unmount();
    history([]);
    expect(screen.queryByRole("button", { name: /^Comparer à la révision lue/ })).toBeNull();
  });

  it("offers no comparison when no revision is read, nor on the revision read", () => {
    const { unmount } = history(["planning.read"], { ...CONTEXT, revisionId: undefined });
    expect(screen.queryByRole("button", { name: /^Comparer à la révision lue/ })).toBeNull();
    unmount();
    history(["planning.read"], { ...CONTEXT, revisionId: OFFER });
    const names = screen.getAllByRole("button", { name: /^Comparer à la révision lue/ });
    expect(names).toHaveLength(1);
    expect(names[0]?.getAttribute("aria-label")).not.toContain("Offre v1.0");
  });

  it("leaves, on the revision read, the other marked revision as the base of its comparison", async () => {
    history(["planning.read"], { ...CONTEXT, revisionId: OFFER });
    await userEvent.click(screen.getByRole("button", { name: /^Comparer à la révision lue/ }));
    expect(screen.getByRole("menuitem").getAttribute("href")).toBe(
      `/projects/${PROJECT}/revisions/${OFFER}/planning?base_revision_id=${REFERENCE}`,
    );
  });
});
