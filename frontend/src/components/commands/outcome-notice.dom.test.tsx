// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { OutcomeNotice } from "./outcome-notice";
import { rejected } from "./rejection";

type Problem = components["schemas"]["Problem"];

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
});
