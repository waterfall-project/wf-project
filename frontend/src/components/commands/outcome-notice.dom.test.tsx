// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen } from "@testing-library/react";
import { RouterContext } from "next/dist/shared/lib/router-context.shared-runtime";
import type { NextRouter } from "next/router";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import { ACCOUNT_DEACTIVATED_DIGEST, SESSION_REQUIRED_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";

import { OutcomeNotice } from "./outcome-notice";
import { rejected } from "./rejection";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/account",
  useSearchParams: () => new URLSearchParams(),
}));

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

  it("leads to the sign-in page by a link the browser follows, a whole document, which the router does not take over", () => {
    const lost = Object.assign(new Error("Server Components render"), {
      digest: SESSION_REQUIRED_DIGEST,
    });
    // A router that would take over the links of the page: a link of the router calls it.
    const router = { push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(() => Promise.resolve()) };
    render(
      <RouterContext.Provider value={router as unknown as NextRouter}>
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
          <OutcomeNotice outcome={rejected(lost)} onClear={vi.fn()} />
        </NextIntlClientProvider>
      </RouterContext.Provider>,
    );
    const link = screen.getByRole("link", { name: "Se connecter" });
    expect(link).toHaveAttribute("href", "/login?next=%2Faccount");
    // Whether the click reached the window still to be followed by the browser; then not followed.
    const followed = vi.fn();
    window.addEventListener(
      "click",
      (event) => {
        followed(!event.defaultPrevented);
        event.preventDefault();
      },
      { once: true },
    );
    fireEvent.mouseEnter(link);
    fireEvent.click(link);
    expect(followed).toHaveBeenCalledWith(true);
    expect(router.push).not.toHaveBeenCalled();
    expect(router.prefetch).not.toHaveBeenCalled();
  });

  it("says a deactivated account without leading to the sign-in page, which would loop", () => {
    const lost = Object.assign(new Error("Server Components render"), {
      digest: SESSION_REQUIRED_DIGEST,
    });
    const deactivated = Object.assign(new Error("Server Components render"), {
      digest: ACCOUNT_DEACTIVATED_DIGEST,
    });
    const notice = (error: Error) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <OutcomeNotice outcome={rejected(error)} onClear={vi.fn()} />
      </NextIntlClientProvider>
    );
    // A session lost leads to the sign-in page: the control of the absence below.
    const { rerender } = render(notice(lost));
    expect(screen.getByRole("link", { name: "Se connecter" })).toBeInTheDocument();
    rerender(notice(deactivated));
    expect(screen.getByRole("alert")).toHaveTextContent("Ce compte est désactivé");
    expect(screen.queryByRole("link", { name: "Se connecter" })).toBeNull();
  });
});
