// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { account, accounts, grid, heldActivation, holdRoute, told, writes } from "@/test/accounts";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  type Problem,
} from "@/test/fixtures";

// The server of Next, as far as the screen needs it: the fake back, the address it reads and the
// navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(),
}));

type Schemas = components["schemas"];

/** Serve the fake back, which keeps the settings of the grid, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient({ "PATCH /me/preferences": "preferences", ...answers }, timing);
  server.client = client;
  return client;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  serve({});
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
  router.replace.mockClear();
  refresh.mockReset();
});

describe("the link to set the password", () => {
  it("gives the link of a local account in a dialog, whole and selected, with the instant it ceases to be valid; the focus back on its cell once closed", async () => {
    const client = serve({
      "POST /users/{user_id}/password-link": { status: 201, example: "password_setup_link" },
    });
    render(accounts());
    const command = within(grid()).getByRole("button", {
      name: "Lien de fixation du mot de passe de « Camille Martin »",
    });
    await userEvent.click(command);
    const dialog = await screen.findByRole("dialog", {
      name: "Lien de fixation du mot de passe de « Camille Martin »",
    });
    const link = (example("password_setup_link") as Schemas["PasswordSetupLink"]).url;
    const field = within(dialog).getByRole("textbox", { name: "Lien" });
    expect(field).toHaveValue(link);
    expect(field).toHaveAttribute("readonly");
    expect(dialog.querySelector("time")).toHaveAttribute("datetime", "2026-06-03T15:05:00Z");
    expect(writes(client).map(([, path]) => path)).toEqual([
      `/users/${account("Martin").user_id}/password-link`,
    ]);
    await userEvent.click(within(dialog).getByRole("button", { name: "Fermer" }));
    await waitFor(() => {
      expect(command.closest("td")).toHaveFocus();
    });
    // Given once, the link is shown no more.
    expect(screen.queryByDisplayValue(link)).toBeNull();
  });

  it("presents the link of a deactivated local account unavailable, naming the condition it lacks, and asks nothing", async () => {
    const client = serve({});
    render(accounts());
    const command = within(grid()).getByRole("button", {
      name: "Lien de fixation du mot de passe de « Alix Moreau »",
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription("Condition non remplie : compte actif.");
    await userEvent.click(command);
    expect(told().textContent).toBe(
      "Lien de fixation du mot de passe de « Alix Moreau » : Condition non remplie : compte actif.",
    );
    expect(writes(client)).toEqual([]);
  });

  it("marks the link of an account busy and unavailable while its deactivation is asked, a press asking nothing", async () => {
    const held = heldActivation();
    const client = serve({ "PUT /users/{user_id}/activation": "user_deactivated" }, held.timing);
    render(accounts());
    const command = within(grid()).getByRole("button", {
      name: "Lien de fixation du mot de passe de «\u00a0Noé Vidal\u00a0»",
    });
    await userEvent.click(
      within(grid()).getByRole("switch", { name: "Compte de «\u00a0Noé Vidal\u00a0» actif" }),
    );
    await waitFor(() => {
      expect(command).toHaveAttribute("aria-busy", "true");
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
    held.release();
    // Deactivated, the account is given no link: the command stays unavailable.
    await waitFor(() => {
      expect(command).toHaveAttribute("aria-busy", "false");
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(writes(client).map(([route]) => route)).toEqual(["PUT /users/{user_id}/activation"]);
  });

  it("asks one link at a time, the other commands of the link busy and unavailable the while", async () => {
    const held = holdRoute("POST /users/{user_id}/password-link");
    const client = serve(
      { "POST /users/{user_id}/password-link": { status: 201, example: "password_setup_link" } },
      held.timing,
    );
    render(accounts());
    const martin = within(grid()).getByRole("button", {
      name: "Lien de fixation du mot de passe de «\u00a0Camille Martin\u00a0»",
    });
    const petit = within(grid()).getByRole("button", {
      name: "Lien de fixation du mot de passe de «\u00a0Lucas Petit\u00a0»",
    });
    await userEvent.click(martin);
    await userEvent.click(petit);
    expect(petit).toHaveAttribute("aria-busy", "true");
    expect(petit).toHaveAttribute("aria-disabled", "true");
    held.release();
    const dialog = await screen.findByRole("dialog", {
      name: "Lien de fixation du mot de passe de «\u00a0Camille Martin\u00a0»",
    });
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    expect(writes(client).map(([, path]) => path)).toEqual([
      `/users/${account("Martin").user_id}/password-link`,
    ]);
    // The link closed, the other commands of the link are available again.
    await userEvent.click(within(dialog).getByRole("button", { name: "Fermer" }));
    await waitFor(() => {
      expect(petit).toHaveAttribute("aria-busy", "false");
    });
    expect(petit).not.toHaveAttribute("aria-disabled");
    await userEvent.click(petit);
    expect(
      await screen.findByRole("dialog", {
        name: "Lien de fixation du mot de passe de «\u00a0Lucas Petit\u00a0»",
      }),
    ).toBeInTheDocument();
    expect(writes(client).map(([, path]) => path)).toEqual([
      `/users/${account("Martin").user_id}/password-link`,
      `/users/${account("Petit").user_id}/password-link`,
    ]);
  });

  it.each([
    [
      "the account deactivated since it was read",
      example("password_link_deactivated") as Problem & { status: 409 },
      "Condition non remplie : compte actif.",
    ],
    [
      "the identity provider silent",
      {
        code: "COMPONENT_UNAVAILABLE",
        status: 503,
        params: { component: "identity_provider" },
      } satisfies Problem & { status: 503 },
      "Fournisseur d’identité",
    ],
  ])(
    "tells above the table the link the server refuses — %s —, the focus back on its command once dismissed",
    async (_, problem, said) => {
      serve({ "POST /users/{user_id}/password-link": { problem } });
      render(accounts());
      const command = within(grid()).getByRole("button", {
        name: "Lien de fixation du mot de passe de «\u00a0Camille Martin\u00a0»",
      });
      await userEvent.click(command);
      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(said);
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(command).not.toHaveAttribute("aria-disabled");
      await userEvent.click(within(alert).getByRole("button", { name: /Fermer l’avis/ }));
      expect(screen.queryByRole("alert")).toBeNull();
      expect(command).toHaveFocus();
    },
  );
});

describe("the email of the link to set the password", () => {
  const ROUTE = "POST /users/{user_id}/invitation";

  it("has the email sent again to a local account, says it went and gives the hand back, the link untouched [WF-ADM-0140-A]", async () => {
    const client = serve({ [ROUTE]: { status: 204 } });
    render(accounts());
    const command = within(grid()).getByRole("button", {
      name: "Renvoyer le courriel de fixation du mot de passe de « Camille Martin »",
    });
    await userEvent.click(command);
    await waitFor(() => {
      expect(told().textContent).toBe(
        "Courriel de fixation du mot de passe renvoyé à « Camille Martin ».",
      );
    });
    expect(writes(client).map(([, path]) => path)).toEqual([
      `/users/${account("Martin").user_id}/invitation`,
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(command).toHaveAttribute("aria-busy", "false");
  });

  it("tells a provider that sends no email as a refusal, never as an email sent [WF-ADM-0140-A]", async () => {
    serve({ [ROUTE]: { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } } });
    render(accounts());
    await userEvent.click(
      within(grid()).getByRole("button", {
        name: "Renvoyer le courriel de fixation du mot de passe de « Camille Martin »",
      }),
    );
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeVisible();
    });
    expect(told().textContent).not.toContain("renvoyé");
  });

  it("presents the email of a deactivated local account unavailable, naming the condition it lacks, and asks nothing [WF-ADM-0140-A]", async () => {
    const client = serve({});
    render(accounts());
    const command = within(grid()).getByRole("button", {
      name: "Renvoyer le courriel de fixation du mot de passe de « Alix Moreau »",
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription("Condition non remplie\u00a0: compte actif.");
    await userEvent.click(command);
    expect(writes(client)).toEqual([]);
  });
});
