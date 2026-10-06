// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { refresh } from "next/cache";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import type { Project } from "@/components/context/reading";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
} from "@/test/fixtures";

import { LifecycleCommands } from "./object-commands";

// The server of Next, as far as an exit needs it: the fake back behind serverClient, and the
// render of the page again once the exit is applied.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/lifecycle",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const EXIT = "POST /projects/{project_id}/exit";
const CONFLICT = {
  problem: {
    code: "STATE_FORBIDS_OPERATION",
    status: 409,
    params: { conflicting_object_id: PROJECT },
  },
} as const;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing?: FakeTiming): FakeClient {
  const client = fakeClient(answers, timing);
  server.client = client;
  return client;
}

/** The exits of a project of the contract, in French. */
function exitsOf(name: string) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <main>
        <LifecycleCommands project={example(name) as Project} />
      </main>
    </NextIntlClientProvider>
  );
}

/** Render the exits of a project of the contract. */
function open(name = "project") {
  return render(exitsOf(name));
}

/** The bodies sent to take the project out of its lifecycle. */
function exits(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === EXIT).map((call) => call.body);
}

/** What the live regions of the exits say, the silent ones left out. */
function said(): (string | null)[] {
  return screen
    .getAllByRole("status")
    .map((status) => status.textContent)
    .filter(Boolean);
}

/** An exit, by its name. */
function exit(name: string) {
  return screen.getByRole("button", { name });
}

/** Open the confirmation of an exit and confirm it. */
async function confirm(name: string) {
  await userEvent.click(exit(name));
  await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));
}

beforeEach(() => {
  vi.mocked(refresh).mockClear();
  server.client = undefined;
});

describe("the exits of the lifecycle of a project", () => {
  it("offers the exits alone, in the order of the server: no command to create or modify", () => {
    open();
    const region = screen.getByRole("region", { name: "Commandes" });
    expect(
      within(region)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual(["Terminer le projet", "Déclarer le projet perdu", "Abandonner le projet"]);
  });

  it("on a project in pricing, presents completion unavailable, naming the condition it lacks [WF-IHM-0090-A]", async () => {
    // Sur un projet en chiffrage, la commande de terminaison est présentée indisponible en
    // nommant la condition manquante.
    const client = serve({});
    const { container } = open("project_pricing");
    const complete = exit("Terminer le projet");
    expect(complete).toHaveAttribute("aria-disabled", "true");
    expect(complete).toHaveAccessibleDescription("Condition non remplie\u00A0: projet en cours.");
    // Pressed, it opens nothing and asks nothing.
    await userEvent.click(complete);
    expect(screen.queryByRole("form")).toBeNull();
    expect(exits(client)).toEqual([]);
    await expectAccessible(container);
  });

  it("confirms an exit before it is applied, naming the state it leads to and that the project becomes read only", async () => {
    const client = serve({ [EXIT]: "project_completed" });
    const { container } = open();
    const complete = exit("Terminer le projet");
    await userEvent.click(complete);
    expect(complete).toHaveAttribute("aria-expanded", "true");

    const form = screen.getByRole("form", { name: "Terminer le projet" });
    // What the user reads, the no-break spaces of French typography aside.
    expect(form.textContent.replaceAll(" ", " ")).toContain(
      "Cette sortie est définitive : le projet passera à l’état « Terminé », et lui comme toutes ses données",
    );
    // A screen reader hears it too, on the field of the motive and on the button that confirms.
    const reason = within(form).getByRole("textbox", { name: "Motif (facultatif)" });
    const confirmation = within(form).getByRole("button", { name: "Confirmer la sortie" });
    for (const described of [reason, confirmation]) {
      expect(described).toHaveAccessibleDescription(/définitive.*Terminé.*lecture seule/);
    }
    // Nothing is asked of the API before the user confirms.
    expect(exits(client)).toEqual([]);
    expect(reason).toHaveFocus();
    await expectAccessible(container);

    await userEvent.type(reason, "Recette prononcée");
    await userEvent.click(confirmation);

    expect(client.calls.find((call) => call.route === EXIT)?.path).toBe(
      `/projects/${PROJECT}/exit`,
    );
    expect(exits(client)).toEqual([
      { to_state: "completed", confirmed: true, reason: "Recette prononcée" },
    ]);
    // The page is rendered again, the confirmation closes, and the new state is said.
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
      expect(screen.queryByRole("form")).toBeNull();
    });
    expect(complete).toHaveFocus();
    expect(said()).toEqual(["Le projet est passé à l’état «\u00A0Terminé\u00A0»."]);
  });

  it("keeps saying the new state once the page is read again, the project completed and its exits unavailable", async () => {
    serve({ [EXIT]: "project_completed" });
    const view = open();
    await confirm("Terminer le projet");
    view.rerender(exitsOf("project_completed"));
    expect(said()).toEqual(["Le projet est passé à l’état «\u00A0Terminé\u00A0»."]);
    expect(exit("Terminer le projet")).toHaveFocus();
    for (const name of ["Terminer le projet", "Déclarer le projet perdu", "Abandonner le projet"]) {
      expect(exit(name)).toHaveAttribute("aria-disabled", "true");
    }
    expect(exit("Abandonner le projet")).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: projet non clos.",
    );
  });

  it("sends no motive when the user gives none", async () => {
    const client = serve({ [EXIT]: "project_completed" });
    open();
    await userEvent.click(exit("Abandonner le projet"));
    await userEvent.type(screen.getByRole("textbox", { name: "Motif (facultatif)" }), "   ");
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));
    expect(exits(client)).toEqual([{ to_state: "abandoned", confirmed: true }]);
  });

  it("opens one confirmation at a time", async () => {
    serve({});
    open();
    await userEvent.click(exit("Terminer le projet"));
    await userEvent.click(exit("Abandonner le projet"));
    expect(screen.getAllByRole("form").map((form) => form.getAttribute("aria-label"))).toEqual([
      "Abandonner le projet",
    ]);
    expect(exit("Terminer le projet")).toHaveAttribute("aria-expanded", "false");
    expect(exit("Abandonner le projet")).toHaveAttribute("aria-expanded", "true");
  });

  it("reads the page again on a refusal for the state of the project, and no longer offers what the server refused, the focus back on the command", async () => {
    const client = serve({ [EXIT]: CONFLICT });
    const view = open();
    await confirm("Terminer le projet");
    expect(exits(client)).toHaveLength(1);
    // The refusal is told once the server has answered: the page is read again, and the alert names
    // the project the state of which forbids the exit.
    await waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
      expect(screen.getByRole("alert")).toHaveTextContent("Modernisation du poste de commande");
    });
    for (const status of screen.getAllByRole("status")) {
      expect(status).toBeEmptyDOMElement();
    }

    // The page read again: the project was completed meanwhile. The exit withdrawn hides its form at
    // once, but the confirmation is closed by an effect (`withdrawn` → `onClose`), a commit later:
    // waited for, not assumed (one failure under a load of 7, #315).
    view.rerender(exitsOf("project_completed"));
    await waitFor(() => {
      expect(screen.queryByRole("form")).toBeNull();
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Modernisation du poste de commande");
    const complete = exit("Terminer le projet");
    expect(complete).toHaveFocus();
    expect(complete).toHaveAttribute("aria-disabled", "true");
    expect(complete).toHaveAttribute("aria-expanded", "false");
    expect(complete).toHaveAccessibleDescription("Condition non remplie\u00A0: projet en cours.");
  });

  it("keeps the confirmation while the API is asked, and says its refusal once it answers", async () => {
    let answer: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      answer = resolve;
    });
    serve({ [EXIT]: CONFLICT }, { hold: () => held });
    open();
    await confirm("Terminer le projet");
    const cancel = screen.getByRole("button", { name: "Annuler" });
    expect(cancel).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(cancel);
    expect(screen.getByRole("form", { name: "Terminer le projet" })).toBeInTheDocument();

    await act(async () => {
      answer();
      await held;
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Modernisation du poste de commande",
    );
    // Cancel is offered again once the transition has settled, a commit after the refusal is shown.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Annuler" })).not.toHaveAttribute("aria-disabled");
    });
  });

  it("says the permission the API finds missing, and reads nothing again", async () => {
    serve({
      [EXIT]: {
        problem: {
          code: "PERMISSION_MISSING",
          status: 403,
          params: { missing_permission: "project_exit" },
        },
      },
    });
    open();
    await confirm("Abandonner le projet");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the API out of reach, and the screen stays", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    open();
    await confirm("Abandonner le projet");
    expect(screen.getByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(screen.getByRole("form", { name: "Abandonner le projet" })).toBeInTheDocument();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("closes without asking anything when cancelled, the focus back on the command", async () => {
    const client = serve({});
    open();
    const abandon = exit("Abandonner le projet");
    await userEvent.click(abandon);
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form")).toBeNull();
    expect(abandon).toHaveFocus();
    expect(abandon).toHaveAttribute("aria-expanded", "false");
    expect(exits(client)).toEqual([]);
  });
});
