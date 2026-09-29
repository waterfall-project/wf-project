// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { requestLanguage } from "@/i18n/request";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

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

/**
 * Render the shell as the root layout does: the language of the request, then the page. The
 * mode and the navigation are not this file's: they are left out, and their reads with them.
 */
async function layout() {
  const { locale, preference } = await requestLanguage();
  return (
    <Shell
      locale={locale}
      preference={preference}
      theme={undefined}
      permissions={undefined}
      remembered={undefined}
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

beforeEach(() => {
  server.refresh = () => undefined;
});

describe("the language selector", () => {
  it("offers the browser's language, French and English, in the language of the page", async () => {
    await open({ "GET /session": "session" });
    const select = screen.getByRole("combobox", { name: "Langue" });
    expect(select).toHaveValue("default");
    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Langue du navigateur", "Français", "English"]);
  });

  it("applies the chosen language without signing in again [WF-INTF-0160-A]", async () => {
    // The back keeps the choice, and the next read of the session returns it; the fake back
    // keeps nothing, so the second answer of GET /session stands in for what it would keep.
    const client = await open({
      "GET /session": ["session", "session_english"],
      [PREFERENCES]: "preferences",
    });

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Langue" }), "en");
    await userEvent.click(screen.getByRole("button", { name: "Appliquer la langue" }));

    const select = await screen.findByRole("combobox", { name: "Language" });
    expect(select).toHaveValue("en");
    expect(screen.getByRole("option", { name: "Browser language" })).toBeInTheDocument();
    expect(sent(client, PREFERENCES)).toEqual([{ language: "en" }]);
    // Two reads of the session and one write: no session was opened anew.
    expect(client.calls.map((call) => call.route)).toEqual([
      "GET /session",
      PREFERENCES,
      "GET /session",
    ]);
  });

  it("sends nothing until the choice is applied, and keeps the focus on the keyboard", async () => {
    const client = await open({
      "GET /session": ["session", "session_english"],
      [PREFERENCES]: "preferences",
    });
    // The logo, which leads home, comes first; the selector next.
    await userEvent.tab();
    await userEvent.tab();
    const select = screen.getByRole("combobox", { name: "Langue" });
    expect(select).toHaveFocus();

    await userEvent.selectOptions(select, "fr");
    await userEvent.selectOptions(select, "en");
    expect(select).toHaveFocus();
    expect(sent(client, PREFERENCES)).toEqual([]);

    await userEvent.tab();
    await userEvent.keyboard("{Enter}");

    const apply = await screen.findByRole("button", { name: "Apply language" });
    expect(apply).toHaveFocus();
    expect(apply.closest("form")).toHaveAttribute("aria-busy", "false");
    expect(sent(client, PREFERENCES)).toEqual([{ language: "en" }]);
  });

  it("leads to the sign-in page, which comes back to the screen, when the session is gone", async () => {
    const expired = { problem: { code: "SESSION_EXPIRED", status: 401 } } as const;
    const refresh = vi.fn();
    const client = await open({ "GET /session": "session", [PREFERENCES]: expired });
    server.refresh = refresh;

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Langue" }), "fr");
    await userEvent.click(screen.getByRole("button", { name: "Appliquer la langue" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Votre session a expiré\u202F; reconnectez-vous.Se connecter");
    const signIn = within(alert).getByRole("link", { name: "Se connecter" });
    const next = new URL(signIn.getAttribute("href") ?? "", "http://front.invalid");
    expect(next.pathname).toBe("/login");
    expect(next.searchParams.get("next")).toBe(`${SCREEN}?revision_id=${REVISION}`);
    expect(sent(client, PREFERENCES)).toEqual([{ language: "fr" }]);
    expect(refresh).not.toHaveBeenCalled();
    expect(screen.getByRole("combobox", { name: "Langue" })).toHaveValue("fr");
  });

  it("says the API is out of reach rather than leave the page blank", async () => {
    await open({ "GET /session": "session" });
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Langue" }), "en");
    await userEvent.click(screen.getByRole("button", { name: "Appliquer la langue" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Le service est injoignable\u202F; réessayez dans un instant.");
    expect(screen.getByRole("combobox", { name: "Langue" })).toHaveValue("en");
  });

  it("shows the preference a new render reads, not the one it was first given", async () => {
    // The account changed elsewhere — another tab, another workstation — and the page is
    // rendered again.
    const client = fakeClient({ "GET /session": ["session", "session_english"] });
    server.client = client;
    const view = render(await layout());
    expect(screen.getByRole("combobox", { name: "Langue" })).toHaveValue("default");

    view.rerender(await layout());

    expect(screen.getByRole("combobox", { name: "Language" })).toHaveValue("en");
  });

  it("keeps the last preference chosen when handed a value that is not one", async () => {
    const client = await open({ "GET /session": "session", [PREFERENCES]: "preferences" });
    fireEvent.change(screen.getByRole("combobox", { name: "Langue" }), {
      target: { value: "de" },
    });
    await userEvent.click(screen.getByRole("button", { name: "Appliquer la langue" }));
    await waitFor(() => {
      expect(sent(client, PREFERENCES)).toEqual([{ language: "default" }]);
    });
  });
});
