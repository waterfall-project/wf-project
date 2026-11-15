// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { holdReading, Reading, releaseReading } from "@/test/held-reading";

import { CODE_LENGTH, ReferenceForm, required } from "./reference-form";

// The form reads the screen anew when a write is lost once sent (`useReadAnew`, US-2240).
const router = vi.hoisted(() => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
}));

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
function form(ask: () => Promise<Outcome<never>>, rules = refusingCode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ReferenceForm
        kind="org_node"
        title="Nouveau nœud"
        hint="Le code est requis."
        creating
        fields={[required("code", "Code", CODE_LENGTH)]}
        initial={{}}
        rules={rules}
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

  it("holds the submit, aria-disabled, until the screen has been read anew after a write whose connection was lost once sent, then gives it back (US-2240)", async () => {
    router.refresh.mockReset();
    holdReading(router.refresh);
    const ask = vi.fn(() => Promise.resolve<Outcome<never>>({ kind: "unreachable", sent: true }));
    render(
      form(ask, () => new Map()),
      { wrapper: Reading },
    );
    const dialog = screen.getByRole("dialog", { name: "Nouveau nœud" });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Code" }), "DT");
    const submit = within(dialog).getByRole("button", { name: "Créer" });
    await userEvent.click(submit);
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("a pu aboutir");
    expect(submit).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(submit);
    expect(ask).toHaveBeenCalledTimes(1);

    await act(async () => {
      releaseReading();
      await Promise.resolve();
    });
    expect(submit).not.toHaveAttribute("aria-disabled");
  });
});
