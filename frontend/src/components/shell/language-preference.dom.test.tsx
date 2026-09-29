// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { requestLanguage } from "@/i18n/request";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { Shell } from "./shell";

// The server of Next, as far as the shell needs it: the fake back behind serverClient, the
// Accept-Language of the browser, and the refresh a server action asks for, which renders
// the layout again.
const server = vi.hoisted((): { client: ApiClient | undefined; refresh: () => unknown } => ({
  client: undefined,
  refresh: () => undefined,
}));

// The screen the browser shows, which the way to the sign-in page comes back to.
const SCREEN = "/projects/01926f3a-7c00-7000-8000-000000000001/lifecycle";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => SCREEN,
  useSearchParams: () => new URLSearchParams({ revision_id: REVISION }),
}));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR,fr;q=0.9" })),
}));
vi.mock("next/cache", () => ({ refresh: () => server.refresh() }));

const PREFERENCES = "PATCH /me/preferences";
const { user } = example("session") as components["schemas"]["Session"];

/**
 * Render the shell as the root layout does: the language of the request, then the page. The
 * mode and the navigation are not this file's: they are left out, and their reads with them;
 * the account is the one of the session of the contract.
 */
async function layout() {
  const { locale, preference } = await requestLanguage();
  return (
    <Shell
      locale={locale}
      account={user}
      preference={preference}
      theme={undefined}
      permissions={undefined}
      remembered={undefined}
      sidebarOpen
    >
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

/** The button of the avatar, in the language of the page. */
function avatar(name = /^(Compte de|Account of) Camille Martin$/) {
  return screen.getByRole("button", { name });
}

/** Open the menu of the account, then the choice of the language; its values. */
async function languages(entry = /^Langue/) {
  await userEvent.click(avatar());
  await userEvent.click(within(screen.getByRole("menu")).getByRole("menuitem", { name: entry }));
  return screen.findAllByRole("menuitemradio");
}

/** Choose a language in the menu of the account. */
async function choose(language: string) {
  await languages();
  await userEvent.click(screen.getByRole("menuitemradio", { name: language }));
}

beforeEach(() => {
  server.refresh = () => undefined;
});

describe("the language in the menu of the account", () => {
  it("offers the browser's language, French and English, in the language of the page", async () => {
    await open({ "GET /session": "session" });
    const values = await languages();
    expect(values.map((value) => value.textContent)).toEqual([
      "Langue du navigateur",
      "Français",
      "English",
    ]);
    expect(screen.getByRole("menuitemradio", { name: "Langue du navigateur" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("menuitem", { name: /^Langue/ })).toHaveTextContent(
      "LangueLangue du navigateur",
    );
  });

  it("applies the chosen language without signing in again [WF-INTF-0160-A]", async () => {
    // The back keeps the choice, and the next read of the session returns it; the fake back
    // keeps nothing, so the second answer of GET /session stands in for what it would keep.
    const client = await open({
      "GET /session": ["session", "session_english"],
      [PREFERENCES]: "preferences",
    });

    await choose("English");

    await waitFor(() => {
      expect(avatar(/^Account of Camille Martin$/)).toBeInTheDocument();
    });
    await languages(/^Language/);
    expect(screen.getByRole("menuitemradio", { name: "English" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("menuitemradio", { name: "Browser language" })).toBeInTheDocument();
    expect(sent(client, PREFERENCES)).toEqual([{ language: "en" }]);
    // Two reads of the session and one write: no session was opened anew.
    expect(client.calls.map((call) => call.route)).toEqual([
      "GET /session",
      PREFERENCES,
      "GET /session",
    ]);
  });

  it("sends nothing while the keyboard moves through the languages, and gives the focus back once one is chosen", async () => {
    const client = await open({
      "GET /session": ["session", "session_english"],
      [PREFERENCES]: "preferences",
    });
    avatar().focus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByRole("menuitem", { name: /^Langue/ })).toHaveFocus();

    await userEvent.keyboard("{ArrowRight}");
    await waitFor(() => {
      expect(screen.getByRole("menuitemradio", { name: "Langue du navigateur" })).toHaveFocus();
    });
    await userEvent.keyboard("{ArrowDown}{ArrowDown}");
    expect(screen.getByRole("menuitemradio", { name: "English" })).toHaveFocus();
    expect(sent(client, PREFERENCES)).toEqual([]);

    await userEvent.keyboard("{Enter}");

    await waitFor(() => {
      expect(avatar(/^Account of Camille Martin$/)).toHaveFocus();
    });
    expect(avatar(/^Account of Camille Martin$/)).toHaveAttribute("aria-busy", "false");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(sent(client, PREFERENCES)).toEqual([{ language: "en" }]);
  });

  it("leads to the sign-in page, which comes back to the screen, when the session is gone", async () => {
    const expired = { problem: { code: "SESSION_EXPIRED", status: 401 } } as const;
    const refresh = vi.fn();
    const client = await open({ "GET /session": "session", [PREFERENCES]: expired });
    server.refresh = refresh;

    await choose("Français");

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Votre session a expiré ; reconnectez-vous.Se connecter");
    const signIn = within(alert).getByRole("link", { name: "Se connecter" });
    const next = new URL(signIn.getAttribute("href") ?? "", "http://front.invalid");
    expect(next.pathname).toBe("/login");
    expect(next.searchParams.get("next")).toBe(`${SCREEN}?revision_id=${REVISION}`);
    expect(sent(client, PREFERENCES)).toEqual([{ language: "fr" }]);
    expect(refresh).not.toHaveBeenCalled();
    // The account kept its preference: the menu says so.
    await languages();
    expect(screen.getByRole("menuitemradio", { name: "Langue du navigateur" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("says the API is out of reach rather than leave the page blank", async () => {
    await open({ "GET /session": "session" });
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });

    await choose("English");

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Le service est injoignable ; réessayez dans un instant.");
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("shows the preference a new render reads, not the one it was first given", async () => {
    // The account changed elsewhere — another tab, another workstation — and the page is
    // rendered again.
    const client = fakeClient({ "GET /session": ["session", "session_english"] });
    server.client = client;
    const view = render(await layout());

    view.rerender(await layout());

    await languages(/^Language/);
    expect(screen.getByRole("menuitemradio", { name: "English" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});
