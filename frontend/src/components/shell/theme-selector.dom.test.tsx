// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { requestSession } from "@/session/request";
import { expectAccessible } from "@/test/axe";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { themePreference } from "@/theme/theme";

import { Shell } from "./shell";

// The server of Next, as far as the shell needs it: the fake back behind serverClient, and
// the refresh a server action asks for, which renders the layout again.
const server = vi.hoisted((): { client: FakeClient | undefined; refresh: () => unknown } => ({
  client: undefined,
  refresh: () => undefined,
}));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: () => server.refresh() }));

const PREFERENCES = "PATCH /me/preferences";

/**
 * Render the shell as the root layout does for the mode: the preference of the account, read
 * once. The language and the navigation are not this file's: French, and left out.
 */
async function layout() {
  const theme = themePreference((await requestSession())?.user);
  return (
    <Shell
      locale="fr"
      preference={undefined}
      theme={theme}
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

/** When the logo shows its dark variant: the media of its dark source, if it has one. */
function darkLogo(): string | null | undefined {
  const picture = screen.getByRole("img", { name: "Waterfall" }).closest("picture");
  return picture?.querySelector("source")?.getAttribute("media");
}

beforeEach(() => {
  server.refresh = () => undefined;
});

describe("the mode selector", () => {
  it("offers the workstation's setting, light and dark, and lets the workstation decide first", async () => {
    await open({ "GET /session": "session" });
    const select = screen.getByRole("combobox", { name: "Mode d’affichage" });
    expect(select).toHaveValue("default");
    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Réglage du poste", "Clair", "Sombre"]);
    expect(darkLogo()).toBe("(prefers-color-scheme: dark)");
    await expectAccessible(document.body);
  });

  it("records the mode chosen in the account, and renders the page in it", async () => {
    // The back keeps the choice, and the next read of the session returns it; the fake back
    // keeps nothing, so the second answer of GET /session stands in for what it would keep.
    const client = await open({
      "GET /session": ["session", "session_dark"],
      [PREFERENCES]: "preferences_dark",
    });

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Mode d’affichage" }),
      "dark",
    );
    await userEvent.click(screen.getByRole("button", { name: "Appliquer le mode" }));

    await waitFor(() => {
      expect(darkLogo()).toBe("all");
    });
    expect(screen.getByRole("combobox", { name: "Mode d’affichage" })).toHaveValue("dark");
    expect(sent(client, PREFERENCES)).toEqual([{ theme: "dark" }]);
    expect(client.calls.map((call) => call.route)).toEqual([
      "GET /session",
      PREFERENCES,
      "GET /session",
    ]);
  });

  it("shows the light variant of the logo alone in a mode forced light", () => {
    render(
      <Shell
        locale="en"
        preference={undefined}
        theme="light"
        permissions={undefined}
        remembered={undefined}
      >
        <main />
      </Shell>,
    );
    expect(darkLogo()).toBeUndefined();
    expect(screen.getByRole("combobox", { name: "Display mode" })).toHaveValue("light");
  });

  it("says why the API refused the choice, and keeps it", async () => {
    const expired = { problem: { code: "SESSION_EXPIRED", status: 401 } } as const;
    const refresh = vi.fn();
    const client = await open({ "GET /session": "session", [PREFERENCES]: expired });
    server.refresh = refresh;

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Mode d’affichage" }),
      "light",
    );
    await userEvent.click(screen.getByRole("button", { name: "Appliquer le mode" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Votre session a expiré ; reconnectez-vous.");
    expect(sent(client, PREFERENCES)).toEqual([{ theme: "light" }]);
    expect(refresh).not.toHaveBeenCalled();
    expect(screen.getByRole("combobox", { name: "Mode d’affichage" })).toHaveValue("light");
  });

  it("keeps the last mode chosen when handed a value that is not one", async () => {
    const client = await open({ "GET /session": "session", [PREFERENCES]: "preferences_dark" });
    fireEvent.change(screen.getByRole("combobox", { name: "Mode d’affichage" }), {
      target: { value: "sepia" },
    });
    await userEvent.click(screen.getByRole("button", { name: "Appliquer le mode" }));
    await waitFor(() => {
      expect(sent(client, PREFERENCES)).toEqual([{ theme: "default" }]);
    });
  });
});
