// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";
import { ROW, UNKNOWN } from "@/test/paste-grid";

import type { PastePlan } from "./columns";
import type { NodesWritten } from "./nodes";
import type { PasteReport } from "./paste";
import { PasteAppliedNotice, PasteDialog } from "./paste-dialog";

/** What a confirmation that wrote two rows of three answers, as the contract gives it. */
type PasteApplied = NodesWritten & { readonly rejected: PasteReport["rejected"] };

/** A component in a language. */
function inLanguage(node: ReactNode, locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {node}
    </NextIntlClientProvider>,
  );
}

/**
 * What the confirmation of the block whose second row names an unknown category did not write,
 * pasted on the label of its first row (`paste_applied_partial`).
 */
const partial = example("paste_applied_partial") as PasteApplied;
const report: PasteReport = {
  target: { row: ROW, column: { label: "label" } },
  written: partial.nodes.length,
  rejected: partial.rejected,
  block: UNKNOWN,
};

describe("the report of a paste", () => {
  it("offers only to abandon a plan that writes no row", () => {
    // A counterfactual variant of `paste_plan_unknown_category`: each row of the block naming the
    // unknown category, one value a row, and so each refused as its second is, none accepted.
    const unknown = example("paste_plan_unknown_category") as PastePlan;
    const block = UNKNOWN.map((cells) => cells.map((cell, at) => (at === 1 ? "Essais" : cell)));
    const [refusal] = unknown.rejected;
    const plan: PastePlan = {
      ...unknown,
      accepted: 0,
      rejected: refusal === undefined ? [] : block.map((_, row) => ({ ...refusal, row })),
    };
    const onApply = vi.fn();
    inLanguage(
      <PasteDialog
        pasting={{
          block,
          width: 4,
          target: report.target,
          plan,
          applying: false,
        }}
        onApply={onApply}
        onAbandon={vi.fn()}
        onClosed={vi.fn()}
      />,
    );
    const dialog = screen.getByRole("dialog", { name: "Coller depuis un tableur" });
    expect(within(dialog).getByRole("status")).toHaveTextContent(
      /^Aucune ligne ne sera écrite\.3 lignes sont refusées :/,
    );
    expect(
      within(dialog)
        .getAllByRole("listitem")
        .map((item) => item.firstElementChild?.textContent),
    ).toEqual(
      [1, 2, 3].map((row) => `Ligne ${row.toString()} du bloc — Catégorie de coût inconnue.`),
    );
    expect(within(dialog).queryByText(/^Confirmé/)).toBeNull();
    expect(
      within(dialog)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual(["Abandonner"]);
    expect(onApply).not.toHaveBeenCalled();
  });
});

describe("the notice of a paste applied", () => {
  it.each([
    [
      "fr",
      `Collage appliqué à partir de la ligne ${ROW.toString()}, colonne « Libellé » : 2 lignes ont été écrites.`,
    ],
    ["en", `Paste applied from row ${ROW.toString()}, column “Label”: 2 rows were written.`],
  ] as const)(
    "says where the block was pasted from, and how many rows were written (%s)",
    (locale, said) => {
      inLanguage(
        <PasteAppliedNotice applied={report} onClear={vi.fn()} onDismissed={vi.fn()} />,
        locale,
      );
      expect(screen.getByRole("alert").firstElementChild).toHaveTextContent(said);
    },
  );

  it("lists the rows refused in a region of its own, named, reached by the keyboard and bounded, the sentence and the command out of it", async () => {
    // However many rows are refused, the grid under the notice stays in the window (#163): the
    // height a region takes is measured by a browser alone, which the journeys would do once the
    // fake back serves a partial paste.
    const { container } = inLanguage(
      <PasteAppliedNotice applied={report} onClear={vi.fn()} onDismissed={vi.fn()} />,
    );
    const refused = screen.getByRole("region", { name: "Lignes refusées par le collage" });
    expect(refused).toHaveAttribute("tabindex", "0");
    expect(refused).toHaveClass("max-h-40", "overflow-y-auto");
    expect(within(refused).getByRole("listitem")).toHaveTextContent(
      "Ligne 2 du bloc — Catégorie de coût inconnue.",
    );
    expect(refused).not.toHaveTextContent(/Collage appliqué/);
    expect(within(refused).queryByRole("button")).toBeNull();
    await expectAccessible(container);
  });

  it("forgets what it told once dismissed, and gives the focus back", async () => {
    const onClear = vi.fn();
    const onDismissed = vi.fn();
    inLanguage(<PasteAppliedNotice applied={report} onClear={onClear} onDismissed={onDismissed} />);
    await userEvent.click(screen.getByRole("button", { name: "Fermer l’avis" }));
    expect(onClear).toHaveBeenCalledOnce();
    expect(onDismissed).toHaveBeenCalledOnce();
  });
});
