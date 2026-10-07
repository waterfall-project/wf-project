// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { OutcomeNotice } from "./outcome-notice";
import { rejected } from "./rejection";

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
});
