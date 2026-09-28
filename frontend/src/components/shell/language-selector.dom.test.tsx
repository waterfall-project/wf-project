// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { requestLanguage } from "@/i18n/request";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { Shell } from "./shell";

// The server of Next, as far as the shell needs it: the fake back behind serverClient, the
// Accept-Language of the browser, and the refresh a server action asks for, which renders
// the layout again.
const server = vi.hoisted((): { client: FakeClient | undefined; refresh: () => unknown } => ({
  client: undefined,
  refresh: () => undefined,
}));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR,fr;q=0.9" })),
}));
vi.mock("next/cache", () => ({ refresh: () => server.refresh() }));

const PREFERENCES = "PATCH /me/preferences";

/** Render the shell as the root layout does: the language of the request, then the page. */
async function layout() {
  const { locale, preference } = await requestLanguage();
  return (
    <Shell locale={locale} preference={preference}>
      <main />
    </Shell>
  );
}

/** Serve the fake back, render the shell, and render it again on each refresh. */
async function open(answers: FakeAnswers): Promise<FakeClient> {
  const client = fakeClient(answers);
  server.client = client;
  const view = render(await layout());
  server.refresh = async () => {
    view.rerender(await layout());
  };
  return client;
}

/** The bodies the shell sent to an operation. */
function sent(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

beforeEach(() => {
  server.refresh = () => undefined;
});

describe("the language selector", () => {
  it("offers the browser's language, French and English, in the language of the page", async () => {
    await open({ "GET /me": "me" });
    const select = screen.getByRole("combobox", { name: "Langue" });
    expect(select).toHaveValue("default");
    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Langue du navigateur", "Français", "English"]);
  });

  it("applies the chosen language without signing in again [WF-INTF-0160-A]", async () => {
    // The back keeps the choice, and the next read of the account returns it; the fake back
    // keeps nothing, so the second answer of GET /me stands in for what it would keep.
    const client = await open({ "GET /me": ["me", "me_english"], [PREFERENCES]: "preferences" });

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Langue" }), "en");
    await userEvent.click(screen.getByRole("button", { name: "Appliquer" }));

    const select = await screen.findByRole("combobox", { name: "Language" });
    expect(select).toHaveValue("en");
    expect(screen.getByRole("option", { name: "Browser language" })).toBeInTheDocument();
    expect(sent(client, PREFERENCES)).toEqual([{ language: "en" }]);
    // Two reads of the account and one write: no new session was asked for.
    expect(client.calls.map((call) => call.route)).toEqual(["GET /me", PREFERENCES, "GET /me"]);
  });

  it("sends nothing until the choice is applied, and keeps the focus on the keyboard", async () => {
    const client = await open({ "GET /me": ["me", "me_english"], [PREFERENCES]: "preferences" });
    await userEvent.tab();
    const select = screen.getByRole("combobox", { name: "Langue" });
    expect(select).toHaveFocus();

    await userEvent.selectOptions(select, "fr");
    await userEvent.selectOptions(select, "en");
    expect(select).toHaveFocus();
    expect(sent(client, PREFERENCES)).toEqual([]);

    await userEvent.tab();
    await userEvent.keyboard("{Enter}");

    const apply = await screen.findByRole("button", { name: "Apply" });
    expect(apply).toHaveFocus();
    expect(apply.closest("form")).toHaveAttribute("aria-busy", "false");
    expect(sent(client, PREFERENCES)).toEqual([{ language: "en" }]);
  });

  it("says why the API refused the choice, in the language of the page", async () => {
    const expired = { problem: { code: "SESSION_EXPIRED", status: 401 } } as const;
    const refresh = vi.fn();
    const client = await open({ "GET /me": "me", [PREFERENCES]: expired });
    server.refresh = refresh;

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Langue" }), "fr");
    await userEvent.click(screen.getByRole("button", { name: "Appliquer" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Votre session a expiré\u202F; reconnectez-vous.");
    expect(sent(client, PREFERENCES)).toEqual([{ language: "fr" }]);
    expect(refresh).not.toHaveBeenCalled();
    expect(screen.getByRole("combobox", { name: "Langue" })).toHaveValue("fr");
  });

  it("shows the preference a new render reads, not the one it was first given", async () => {
    // The account changed elsewhere — another tab, another workstation — and the page is
    // rendered again.
    const client = fakeClient({ "GET /me": ["me", "me_english"] });
    server.client = client;
    const view = render(await layout());
    expect(screen.getByRole("combobox", { name: "Langue" })).toHaveValue("default");

    view.rerender(await layout());

    expect(screen.getByRole("combobox", { name: "Language" })).toHaveValue("en");
  });

  it("keeps the last preference chosen when handed a value that is not one", async () => {
    const client = await open({ "GET /me": "me", [PREFERENCES]: "preferences" });
    fireEvent.change(screen.getByRole("combobox", { name: "Langue" }), {
      target: { value: "de" },
    });
    await userEvent.click(screen.getByRole("button", { name: "Appliquer" }));
    await waitFor(() => {
      expect(sent(client, PREFERENCES)).toEqual([{ language: "default" }]);
    });
  });
});
