// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { refresh } from "next/cache";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { Project } from "@/components/context/reading";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

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

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The exits of a project of the contract, in French. */
function open(name = "project") {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <main>
        <LifecycleCommands project={example(name) as Project} />
      </main>
    </NextIntlClientProvider>,
  );
}

/** The bodies sent to take the project out of its lifecycle. */
function exits(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === EXIT).map((call) => call.body);
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
    const complete = screen.getByRole("button", { name: "Terminer le projet" });
    expect(complete).toHaveAttribute("aria-disabled", "true");
    expect(complete).toHaveAccessibleDescription("Condition non remplie : projet en cours.");
    // Pressed, it opens nothing and asks nothing.
    await userEvent.click(complete);
    expect(screen.queryByRole("form")).toBeNull();
    expect(exits(client)).toEqual([]);
    await expectAccessible(container);
  });

  it("confirms an exit before it is applied, naming the state it leads to and that the project becomes read only", async () => {
    const client = serve({ [EXIT]: "project_completed" });
    const { container } = open();
    const complete = screen.getByRole("button", { name: "Terminer le projet" });
    await userEvent.click(complete);
    expect(complete).toHaveAttribute("aria-expanded", "true");

    const form = screen.getByRole("form", { name: "Terminer le projet" });
    // What the user reads, the no-break spaces of French typography aside.
    expect(form.textContent.replaceAll(" ", " ")).toContain(
      "Cette sortie est définitive : le projet passera à l’état « Terminé », et lui comme toutes ses données",
    );
    expect(form).toHaveTextContent("passeront en lecture seule");
    // Nothing is asked of the API before the user confirms.
    expect(exits(client)).toEqual([]);
    const reason = within(form).getByRole("textbox", { name: "Motif (facultatif)" });
    expect(reason).toHaveFocus();
    await expectAccessible(container);

    await userEvent.type(reason, "Recette prononcée");
    await userEvent.click(within(form).getByRole("button", { name: "Confirmer la sortie" }));

    expect(client.calls.find((call) => call.route === EXIT)?.path).toBe(
      `/projects/${PROJECT}/exit`,
    );
    expect(exits(client)).toEqual([
      { to_state: "completed", confirmed: true, reason: "Recette prononcée" },
    ]);
    // The page is rendered again, the confirmation closes, and the new state is said.
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("form")).toBeNull();
    expect(complete).toHaveFocus();
    expect(
      screen
        .getAllByRole("status")
        .map((status) => status.textContent)
        .filter(Boolean),
    ).toEqual(["Le projet est passé à l’état « Terminé »."]);
  });

  it("sends no motive when the user gives none", async () => {
    const client = serve({ [EXIT]: "project_completed" });
    open();
    await userEvent.click(screen.getByRole("button", { name: "Abandonner le projet" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Motif (facultatif)" }), "   ");
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));
    expect(exits(client)).toEqual([{ to_state: "abandoned", confirmed: true }]);
  });

  it("tells the refusal of the API under the confirmation, and applies nothing", async () => {
    const client = serve({
      [EXIT]: {
        problem: {
          code: "STATE_FORBIDS_OPERATION",
          status: 409,
          params: { conflicting_object_id: PROJECT },
        },
      },
    });
    open();
    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la sortie" }));
    expect(exits(client)).toHaveLength(1);
    const form = screen.getByRole("form", { name: "Terminer le projet" });
    const alert = within(form).getByRole("alert");
    expect(alert).toHaveTextContent("Modernisation du poste de commande");
    expect(refresh).not.toHaveBeenCalled();
    for (const status of screen.getAllByRole("status")) {
      expect(status).toBeEmptyDOMElement();
    }
  });

  it("closes without asking anything when cancelled, the focus back on the command", async () => {
    const client = serve({});
    open();
    const lose = screen.getByRole("button", { name: "Abandonner le projet" });
    await userEvent.click(lose);
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("form")).toBeNull();
    expect(lose).toHaveFocus();
    expect(lose).toHaveAttribute("aria-expanded", "false");
    expect(exits(client)).toEqual([]);
  });
});
