// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { requestSession } from "@/session/request";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { themePreference } from "@/theme/theme";

import { Shell } from "./shell";

// The server of Next, as far as the shell needs it: the fake back behind serverClient, and
// the refresh a server action asks for, which renders the layout again.
const server = vi.hoisted((): { client: FakeClient | undefined; refresh: () => unknown } => ({
  client: undefined,
  refresh: () => undefined,
}));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/cache", () => ({ refresh: () => server.refresh() }));

const PREFERENCES = "PATCH /me/preferences";
const user = example("me") as components["schemas"]["UserSelf"];

/**
 * Render the shell as the root layout does for the mode: the account, and its preference read
 * once. The language and the navigation are not this file's: French, and left out.
 */
async function layout() {
  const account = await requestSession();
  return (
    <Shell
      locale="fr"
      account={account}
      preference={undefined}
      theme={themePreference(account)}
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

/** When the logo shows its dark variant: the media of its dark source, if it has one. */
function darkLogo(): string | null | undefined {
  const picture = screen.getByRole("img", { name: "Waterfall" }).closest("picture");
  return picture?.querySelector("source")?.getAttribute("media");
}

/** Open the menu of the account, then the choice of the mode; its values. */
async function modes(entry = /^Mode d’affichage/) {
  await userEvent.click(screen.getByRole("button", { name: /^(Compte de|Account of) Camille/ }));
  await userEvent.click(within(screen.getByRole("menu")).getByRole("menuitem", { name: entry }));
  return screen.findAllByRole("menuitemradio");
}

/** Choose a mode in the menu of the account. */
async function choose(mode: string) {
  await modes();
  await userEvent.click(screen.getByRole("menuitemradio", { name: mode }));
}

/** The value of the mode the menu has checked. */
function checked(): string | null | undefined {
  return screen
    .getAllByRole("menuitemradio")
    .find((value) => value.getAttribute("aria-checked") === "true")?.textContent;
}

beforeEach(() => {
  server.refresh = () => undefined;
});

describe("the mode selector", () => {
  it("offers the workstation's setting, light and dark, and lets the workstation decide first", async () => {
    await open({ "GET /me": "me" });
    expect(darkLogo()).toBe("(prefers-color-scheme: dark)");
    await expectAccessible(document.body);
    const values = await modes();
    expect(values.map((value) => value.textContent)).toEqual([
      "Réglage du poste",
      "Clair",
      "Sombre",
    ]);
    expect(checked()).toBe("Réglage du poste");
    // The menu open, the page beside it is hidden from a screen reader and out of reach of
    // the keyboard: the menus themselves are what is read.
    for (const menu of screen.getAllByRole("menu")) {
      await expectAccessible(menu);
    }
  });

  it("records the mode chosen in the account, and renders the page in it", async () => {
    // The back keeps the choice, and the next read of the session returns it; the fake back
    // keeps nothing, so the second answer of GET /session stands in for what it would keep.
    const client = await open({
      "GET /me": ["me", "me_dark"],
      [PREFERENCES]: "preferences_dark",
    });

    await choose("Sombre");

    await waitFor(() => {
      expect(darkLogo()).toBe("all");
    });
    expect(sent(client, PREFERENCES)).toEqual([{ theme: "dark" }]);
    await modes();
    expect(checked()).toBe("Sombre");
    expect(client.calls.map((call) => call.route)).toEqual(["GET /me", PREFERENCES, "GET /me"]);
  });

  it("shows the light variant of the logo alone in a mode forced light", async () => {
    render(
      <Shell
        locale="en"
        account={user}
        preference={undefined}
        theme="light"
        permissions={undefined}
        remembered={undefined}
        sidebarOpen
      >
        <main />
      </Shell>,
    );
    expect(darkLogo()).toBeUndefined();
    await modes(/^Display mode/);
    expect(checked()).toBe("Light");
  });

  it("says why the API refused the choice, and shows the mode the account kept", async () => {
    const malformed = { problem: { code: "MALFORMED_REQUEST", status: 400 } } as const;
    const refresh = vi.fn();
    const client = await open({ "GET /me": "me", [PREFERENCES]: malformed });
    server.refresh = refresh;

    await choose("Clair");

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("La requête est mal formée.");
    expect(sent(client, PREFERENCES)).toEqual([{ theme: "light" }]);
    expect(refresh).not.toHaveBeenCalled();
    expect(darkLogo()).toBe("(prefers-color-scheme: dark)");
    await modes();
    expect(checked()).toBe("Réglage du poste");
  });
});
