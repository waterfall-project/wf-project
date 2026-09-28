// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { readContext } from "@/navigation/context";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { ContextBanner } from "./context-banner";
import { availableEdits, isReadOnly, type Revision } from "./read-only";
import type { ContextFilter, Project, ProjectReading, Subproject } from "./reading";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const REMAINING = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;

/** The reading of an address, as the server hands it to the banner, from the examples. */
function reading(address: string, revisionExample: string | undefined): ProjectReading {
  const [pathname = "", query = ""] = address.split("?");
  const context = readContext(pathname, new URLSearchParams(query));
  if (context === undefined) {
    throw new Error(`No context at ${address}`);
  }
  const revision =
    revisionExample === undefined ? undefined : (example(revisionExample) as Revision);
  const subprojects = example("subprojects") as Subproject[];
  const filters: ContextFilter[] = [];
  const subprojectId = context.parameters.get("subproject_id");
  if (subprojectId !== null) {
    const subproject = subprojects.find((one) => one.subproject_id === subprojectId);
    filters.push({ name: "subproject_id", value: subprojectId, subproject });
  }
  const asOf = context.parameters.get("as_of");
  if (asOf !== null) {
    filters.push({ name: "as_of", value: asOf });
  }
  return {
    pathname,
    context,
    project: example("project") as Project,
    revision,
    edits: revision === undefined ? new Set() : availableEdits(revision),
    readOnly: revision !== undefined && isReadOnly(revision),
    filters,
  };
}

/** Render the banner of a reading, in a language. */
function banner(read: ProjectReading, locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <ContextBanner reading={read} />
    </NextIntlClientProvider>,
  );
}

describe("the banner of the reading context", () => {
  it("is a region named for what it holds, which names the project and the revision [WF-IHM-0020-A]", async () => {
    // Chaque écran de données de projet nomme le projet et la révision affichée.
    const { container } = banner(reading(REMAINING, "revision"));
    const region = screen.getByRole("region", { name: "Contexte de lecture" });
    expect(within(region).getByText("Modernisation du poste de commande")).toBeInTheDocument();
    expect(within(region).getByText("Révision en cours")).toBeInTheDocument();
    expect(within(region).getByText("En cours d’élaboration")).toBeInTheDocument();
    expect(within(region).queryByText("Révision de référence")).toBeNull();
    expect(within(region).queryByText(/Lecture seule/)).toBeNull();
    await expectAccessible(container);
  });

  it("presents a marked revision, its version name, that it is the reference, and that it is read only [WF-IHM-0020-A]", async () => {
    // L'ouverture d'une révision marquée présente cet état — la seconde moitié de la phrase,
    // aucune commande de modification proposée, est prouvée avec les commandes (US-0170/L1).
    const { container } = banner(reading(REMAINING, "revision_marked"));
    const region = screen.getByRole("region", { name: "Contexte de lecture" });
    expect(within(region).getByText("Référence")).toBeInTheDocument();
    expect(within(region).getByText("Marquée")).toBeInTheDocument();
    expect(within(region).getByText("Révision de référence")).toBeInTheDocument();
    expect(
      within(region).getByText("Lecture seule : aucune saisie n’est proposée sur cette révision.", {
        normalizer: (text) => text.replace(/\s+/g, " "),
      }),
    ).toBeInTheDocument();
    await expectAccessible(container);
  });

  it("presents as read only a draft the caller may modify nothing of", () => {
    banner(reading(REMAINING, "revision_reader"), "en");
    expect(
      screen.getByText("Read only: no entry is offered on this revision."),
    ).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("shows each active filter as a chip, visible at once, with a link that lifts it [WF-IHM-0020-A]", async () => {
    // Un filtre actif est visible sans avoir à ouvrir le panneau de filtres.
    const address = `${REMAINING}?subproject_id=${SUBPROJECT}&as_of=2026-05-31`;
    const { container } = banner(reading(address, "revision"), "en");
    const chips = screen.getByRole("list", { name: "Active filters" });
    const items = within(chips).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "Subproject: SP-CMD — Poste de commande",
      "Calculation date: 31 May 2026",
    ]);
    expect(items[0]).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Remove the filter “Calculation date: 31 May 2026”" }),
    ).toHaveAttribute("href", `${REMAINING}?subproject_id=${SUBPROJECT}`);
    expect(
      screen.getByRole("link", {
        name: "Remove the filter “Subproject: SP-CMD — Poste de commande”",
      }),
    ).toHaveAttribute("href", `${REMAINING}?as_of=2026-05-31`);
    await expectAccessible(container);
  });

  it("keeps the revision a function of the project carries when a filter is lifted", () => {
    const lifecycle = `/projects/${PROJECT}/lifecycle`;
    banner(reading(`${lifecycle}?revision_id=${REVISION}&subproject_id=unassigned`, "revision"));
    expect(screen.getByRole("listitem")).toHaveTextContent("Sous-projet : Hors sous-projet", {
      normalizeWhitespace: true,
    });
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      `${lifecycle}?revision_id=${REVISION}`,
    );
  });

  it("names a sub-project the project lacks, and a date that is none, as the address gives them", () => {
    const unknown = "01926f3a-7c00-7000-8000-000000000899";
    banner(reading(`${REMAINING}?subproject_id=${unknown}&as_of=2026-02-30`, "revision"), "en");
    expect(screen.getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      `Subproject: ${unknown}`,
      "Calculation date: 2026-02-30",
    ]);
  });

  it("shows the project alone, without chips, on a function of the project without a revision", () => {
    banner(reading(`/projects/${PROJECT}/lifecycle`, undefined));
    const region = screen.getByRole("region", { name: "Contexte de lecture" });
    expect(within(region).getByRole("term")).toHaveTextContent("Projet");
    expect(within(region).getByRole("definition")).toHaveTextContent(
      "Modernisation du poste de commande",
    );
    expect(within(region).queryByText("Révision")).toBeNull();
    expect(within(region).queryByRole("list")).toBeNull();
  });
});
