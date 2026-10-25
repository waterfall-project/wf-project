// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The panel of the online help when the chunk of its Markdown renderer does not load (US-0580): the
 * panel says the help could not be read, in its body, and the screen stays where it is.
 */
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { PageHeader } from "./page-header";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/projects/p/revisions/r/planning",
}));

vi.mock("./help-markdown", () => {
  throw new Error("Loading chunk failed");
});

describe("the panel of the online help", () => {
  it("says a failed reading, not the error page, when the renderer's chunk is rejected [WF-IHM-0140-A]", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const user = userEvent.setup();
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <PageHeader title="Planification" />
      </NextIntlClientProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Aide" }));
    const dialog = await screen.findByRole("dialog", { name: "Planification" });
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "L’aide n’a pas pu être lue.",
    );
    expect(screen.getByRole("button", { name: "Fermer l’aide" })).toBeInTheDocument();
  });
});
