// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider, useTranslations } from "next-intl";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { forgetMessages } from "@/components/notices/message-history";
import { UserCommands } from "./user-commands";
import { account, accounts, grid, writes } from "@/test/accounts";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

// An account whose write is refused as stale (412) is read anew, so that its row shows what the
// server holds and a new try passes (#3078).
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(""),
}));

/** Serve the fake back, which keeps the settings of the grid. */
function serve(answers: FakeAnswers) {
  const client = fakeClient({ "PATCH /me/preferences": "preferences", ...answers });
  server.client = client;
  return client;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  forgetMessages();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the write of a cell refused as stale", () => {
  it("reads an account anew after a 412 of a cell: the row shows its current version and the next write goes from it, the refusal saying what to do [WF-IHM-0110-A] #3078", async () => {
    const client = serve({
      "PUT /users/{user_id}/activation": [
        { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
        "user_reactivated",
      ],
      // Deactivated by someone else meanwhile, from version 2.
      "GET /users/{user_id}": "user_deactivated",
    });
    render(accounts());
    const vidal = account("Vidal");
    const name = "Compte de «\u00a0Noé Vidal\u00a0» actif";
    await userEvent.click(within(grid()).getByRole("switch", { name }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ce compte a été modifié entre-temps. Vérifiez sa ligne, puis refaites la modification si elle vaut encore.",
    );
    // The row shows the account as the server holds it now: deactivated.
    await waitFor(() => {
      expect(within(grid()).getByRole("switch", { name })).not.toBeChecked();
    });
    await userEvent.click(within(grid()).getByRole("switch", { name }));
    // The reading is a call of the fake back too: the writes are its PUT.
    const puts = () =>
      writes(client).filter(([route]) => route === "PUT /users/{user_id}/activation");
    await waitFor(() => {
      expect(puts()).toHaveLength(2);
    });
    expect(puts()[0]?.[2]).toEqual({ is_active: false, lock_version: vidal.lock_version });
    expect(puts()[1]?.[2]).toEqual({ is_active: true, lock_version: 2 });
  });

  it("leaves the row as it was when the reading after a 412 fails itself, the refusal alone told, and a second try goes from the version first held [WF-IHM-0110-A] #3078", async () => {
    const client = serve({
      "PUT /users/{user_id}/activation": { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
      "GET /users/{user_id}": { problem: { code: "NOT_FOUND", status: 404 } },
    });
    render(accounts());
    const vidal = account("Vidal");
    const name = "Compte de «\u00a0Noé Vidal\u00a0» actif";
    await userEvent.click(within(grid()).getByRole("switch", { name }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("refaites la modification si elle vaut encore.");
    expect(alert).not.toHaveTextContent("dernière version");
    expect(screen.getAllByRole("alert")).toHaveLength(1);
    // The row was not replaced: the switch keeps its state.
    expect(within(grid()).getByRole("switch", { name })).toBeChecked();
    await userEvent.click(within(grid()).getByRole("switch", { name }));
    const puts = () =>
      writes(client).filter(([route]) => route === "PUT /users/{user_id}/activation");
    await waitFor(() => {
      expect(puts()).toHaveLength(2);
    });
    expect(puts()[1]?.[2]).toEqual({ is_active: false, lock_version: vidal.lock_version });
  });
});

/** The sentence a 412 is told with, as the subtree it is rendered in holds it. */
function Sentence({ id }: { readonly id: string }) {
  const t = useTranslations("errors");
  return <p data-testid={id}>{t("STALE_LOCK_VERSION")}</p>;
}

describe("the sentence of a stale write", () => {
  it("is the one of the screen of the accounts alone, the others keeping the sentence of the code [WF-IHM-0110-A] #3078", () => {
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <Sentence id="outside" />
        <UserCommands>
          <Sentence id="inside" />
        </UserCommands>
      </NextIntlClientProvider>,
    );
    expect(screen.getByTestId("outside")).toHaveTextContent("Quelqu’un a modifié cette donnée");
    expect(screen.getByTestId("inside")).toHaveTextContent("Vérifiez sa ligne");
  });
});
