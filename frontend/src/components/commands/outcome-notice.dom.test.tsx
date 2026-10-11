// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { NodeList } from "@/components/grid/nodes";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { OutcomeNotice } from "./outcome-notice";
import { rejected } from "./rejection";

type Problem = components["schemas"]["Problem"];

/**
 * The first lines of the main structure of the witness, as a refusal names them: a counterfactual
 * variant of `subproject_delete_estimated` borne by them, the rest of the refusal kept
 * (`refusedFor`).
 */
function borneLines(count: number) {
  const volume = example("volume/nodes_thousand") as NodeList;
  return volume.items
    .filter((node) => node.estimate_line !== undefined && node.estimate_line !== null)
    .slice(0, count)
    .map(({ node_id, row_number, estimate_line }) => ({
      structure_id: "01926f3a-7c00-7000-8000-000000000201",
      node_id,
      row_number,
      label: estimate_line?.label ?? "",
    }));
}

/** The first projects of the portfolio of the witness, as a refusal names them (`projects`). */
function portfolioProjects(count: number) {
  const portfolio = example("volume/portfolio_projects") as {
    items: { label: string; code: string | null }[];
  };
  return portfolio.items
    .slice(0, count)
    .map(({ label, code }) => ({ project_label: label, project_code: code }));
}

/** The notice of a refusal, in French. */
function noticeOf(problem: Problem) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <OutcomeNotice
        outcome={{ kind: "refused", problem, conflictingObjectId: null }}
        onClear={vi.fn()}
      />
    </NextIntlClientProvider>
  );
}

/** The notice of the deletion of a sub-project refused for the lines given, in French. */
function refusedFor(lines: ReturnType<typeof borneLines>) {
  const refused = example("subproject_delete_estimated") as Problem;
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <OutcomeNotice
        outcome={{
          kind: "refused",
          problem: { ...refused, params: { ...refused.params, estimate_lines: lines } },
          conflictingObjectId: null,
        }}
        onClear={vi.fn()}
      />
    </NextIntlClientProvider>
  );
}

describe("the notice of an outcome", () => {
  it("shows the reference of the unexpected error, as the screen of failure does, and of no other refusal", () => {
    const thrown = Object.assign(new Error("Server Components render"), { digest: "3141592653" });
    const { rerender } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <OutcomeNotice outcome={rejected(thrown)} onClear={vi.fn()} />
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      /^Erreur inattendue du service\.\s*Référence\s:\s3141592653$/,
    );
    rerender(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <OutcomeNotice
          outcome={{
            kind: "refused",
            problem: { code: "NOT_FOUND", status: 404, correlation_id: "2718281828" },
            conflictingObjectId: null,
          }}
          onClear={vi.fn()}
        />
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent("Référence");
  });

  it("says the API out of reach for a server action the browser could not reach", () => {
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <OutcomeNotice outcome={rejected(new TypeError("Failed to fetch"))} onClear={vi.fn()} />
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Le service est injoignable");
  });

  it("names the holder of a value taken by the label the refusal gives it, when the screen does not show it, and by its own name otherwise (#714)", () => {
    // The code of the witness given to another project, refused once its dialog is gone: the screen
    // of a project shows no other project, which the refusal names (`project_code_taken`).
    const taken = example("project_code_taken") as Problem;
    const holder = "01926f3a-7c00-7000-8000-000000000001";
    const notice = (names: Record<string, string>) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <OutcomeNotice
          outcome={{ kind: "conflict", problem: taken, conflictingObjectId: holder }}
          names={names}
          onClear={vi.fn()}
        />
      </NextIntlClientProvider>
    );
    const { rerender } = render(notice({}));
    expect(screen.getByRole("alert")).toHaveTextContent(
      /Objet en conflit\s:\sModernisation du poste de commande\.$/,
    );
    rerender(notice({ [holder]: "PRJ-001" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/Objet en conflit\s:\sPRJ-001\.$/);
  });

  it("lists under its sentence the lines a refusal names beyond a few, in a list named, described by the sentence, reached by the keyboard and bounded, out of the alert", async () => {
    const lines = borneLines(6);
    const { container } = render(refusedFor(lines));
    const listed = screen.getByRole("list", { name: "Lignes de devis nommées par le refus" });
    // Out of the alert, which would read the lines at once, however many they are (#765).
    expect(within(screen.getByRole("alert")).queryByRole("list")).toBeNull();
    expect(listed).toHaveAccessibleDescription(/^L’état actuel ne permet pas cette opération\./);
    expect(listed).toHaveAccessibleDescription(/6 lignes de devis .* listées ci-dessous\./);
    expect(listed).toHaveAttribute("tabindex", "0");
    expect(listed).toHaveClass("max-h-40", "overflow-y-auto");
    expect(
      within(listed)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(
      lines.map((line) => `ligne ${line.row_number.toString()} «\u00a0${line.label}\u00a0»`),
    );
    await expectAccessible(container);
  });

  it("lists under its sentence the projects a refusal names beyond a few, in a list named, described by the sentence, reached by the keyboard and bounded, out of the alert", async () => {
    // A variant of `calendar_update_without_hours`: six projects of the portfolio in cause, the one
    // value changed.
    const refused = example("calendar_update_without_hours") as Problem;
    const projects = portfolioProjects(6);
    const { container } = render(noticeOf({ ...refused, params: { ...refused.params, projects } }));
    const listed = screen.getByRole("list", { name: "Projets nommés par le refus" });
    expect(within(screen.getByRole("alert")).queryByRole("list")).toBeNull();
    expect(listed).toHaveAccessibleDescription(/^Une tâche n’aurait plus aucune heure/);
    expect(listed).toHaveAccessibleDescription(/6 projets en cause, listés ci-dessous\.$/);
    expect(listed).toHaveAttribute("tabindex", "0");
    expect(listed).toHaveClass("max-h-40", "overflow-y-auto");
    expect(
      within(listed)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(
      projects.map(({ project_label, project_code }) => `${project_label} (${project_code ?? ""})`),
    );
    await expectAccessible(container);
  });

  it("names five projects in its sentence, and lists none", () => {
    // A variant of `calendar_update_without_hours`: five projects of the portfolio in cause, the
    // one value changed — the most the sentence names.
    const refused = example("calendar_update_without_hours") as Problem;
    render(noticeOf({ ...refused, params: { ...refused.params, projects: portfolioProjects(5) } }));
    expect(screen.queryByRole("list", { name: "Projets nommés par le refus" })).toBeNull();
    expect(screen.getByRole("alert")).toHaveTextContent(
      /Projets en cause : Modernisation du poste de commande \(PRJ-001\), .* et Automatisation du poste de commande — Lyon \(PRJ-005\)\.$/,
    );
  });

  it("names five lines in its sentence, and lists none", () => {
    const lines = borneLines(5);
    render(refusedFor(lines));
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.getByRole("alert")).toHaveTextContent(
      `qui portent le sous-projet : ligne ${(lines[0]?.row_number ?? 0).toString()} «`,
    );
  });
});
