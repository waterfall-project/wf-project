// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";

import { CODE_LENGTH, ReferenceForm, required } from "./reference-form";

type FieldProblem = components["schemas"]["FieldProblem"];

/**
 * A rule between fields that refuses the code whatever it holds, as a rule points at the one field
 * that breaks it: what no form of the screens does, the rules of each judging the fields that passed
 * alone — the order of the refusals, which they never meet, is proven here (#738).
 */
function refusingCode(): ReadonlyMap<string, FieldProblem> {
  return new Map([["code", { pointer: "/code", code: "BOUNDS_NOT_ORDERED" }]]);
}

/** The form of a code alone, in French, under the rule given. */
function form(ask: () => Promise<never>) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ReferenceForm
        kind="org_node"
        title="Nouveau nœud"
        hint="Le code est requis."
        creating
        fields={[required("code", "Code", CODE_LENGTH)]}
        initial={{}}
        rules={refusingCode}
        ask={ask}
        target={undefined}
        answering={(answer) => answer}
        onDone={vi.fn()}
        onClose={vi.fn()}
        onClosed={vi.fn()}
      />
    </NextIntlClientProvider>
  );
}

describe("the form of the reference data", () => {
  it("says at a field its own refusal rather than that of a rule it breaks too, and the rule's once it passes, asking nothing", async () => {
    const ask = vi.fn(() => Promise.reject(new Error("never asked")));
    render(form(ask));
    const dialog = screen.getByRole("dialog", { name: "Nouveau nœud" });
    const code = within(dialog).getByRole("textbox", { name: "Code" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    expect(code).toHaveAccessibleDescription("Une valeur est requise.");
    await userEvent.type(code, "DT");
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    expect(code).toHaveAccessibleDescription("Les bornes doivent être strictement croissantes.");
    expect(ask).not.toHaveBeenCalled();
  });
});
