// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { IdentitySync, type IdentitySyncReport } from "./identity-sync";

// The server of Next, as far as the reading needs it: the fake back behind serverClient.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
// The router of Next, as far as the tracker needs it: the refresh that reads the screen anew.
const router = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(),
}));

const START = "POST /identity-syncs";
const TASK = "GET /tasks/{task_id}";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A report of the contract, by the name of its example. */
function report(name: string): IdentitySyncReport {
  return example(name) as IdentitySyncReport;
}

/** The section of the reading, with the report given, within the shell that follows the tasks. */
function open(shown: IdentitySyncReport | undefined, startable = true) {
  const tree = (given: IdentitySyncReport | undefined) => (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TaskPanel />
        <main>
          <IdentitySync report={given} startable={startable} />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
  const rendered = render(tree(shown));
  return {
    ...rendered,
    show: (given: IdentitySyncReport) => {
      rendered.rerender(tree(given));
    },
  };
}

/** The section of the reading of the accounts. */
function section() {
  return screen.getByRole("region", { name: "Lecture des comptes du fournisseur d’identité" });
}

/** Open the details of the last reading, and give them. */
async function details() {
  await userEvent.click(screen.getByRole("button", { name: "Détails de la dernière lecture" }));
  return screen.getByRole("region", { name: "Détails de la dernière lecture" });
}

/** Let the time of one read of the task go by, and the read be answered. */
async function tick() {
  await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
}

beforeEach(() => {
  router.refresh.mockClear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the reading of the accounts", () => {
  it("gives the hand back as soon as the reading is queued, follows it to its end, and the user sees it ended and its report [WF-ARC-0090-A]", async () => {
    // La lecture des comptes ne tient aucune requête au-delà de la création de la tâche, et
    // l'utilisateur en voit l'aboutissement : the command answers with the task queued, the
    // tracker reads it until it has succeeded, announces it, and offers to read the screen anew,
    // where the report of the reading shows.
    const client = serve({
      [START]: { example: "identity_sync_queued", status: 202 },
      [TASK]: "identity_sync_succeeded",
    });
    const { show } = open(report("identity_sync_report"));

    await userEvent.click(within(section()).getByRole("button", { name: "Lire les comptes" }));
    expect(client.calls.map((call) => call.route)).toEqual([START]);
    const tasks = screen.getByRole("region", { name: "Tâches de fond" });
    expect(within(tasks).getByText("En attente")).toBeVisible();
    // Nothing of the screen is withheld while the worker reads.
    expect(document.querySelector("[aria-modal], [inert], :disabled")).toBeNull();

    await tick();
    expect(client.calls.filter((call) => call.route === TASK).map((call) => call.path)).toEqual([
      "/tasks/01926f3a-7c00-7000-8000-000000000941",
    ]);
    expect(within(tasks).getByText("Réussie")).toBeVisible();
    expect(within(tasks).getByRole("log").textContent).toBe(
      "Tâche terminée : Lecture des comptes du fournisseur d’identité.",
    );
    // Its result is a report to read on the screen, not a file to download.
    expect(within(tasks).queryByRole("link", { name: /Télécharger/ })).toBeNull();
    await userEvent.click(within(tasks).getByRole("button", { name: "Recharger l’écran" }));
    expect(router.refresh).toHaveBeenCalledOnce();

    // The screen read anew shows the report of the reading that has just ended.
    show(report("identity_sync_report_flagged"));
    expect(within(section()).getByText("2 comptes créés, sans rôle")).toBeVisible();
  });

  it("presents what the last reading did, the last administrator kept and reported, a person without an address named by her identifier at the provider, each by the motive of the catalogue [WF-ADM-0070-A]", async () => {
    serve({});
    const { container } = open(report("identity_sync_report_flagged"));
    const counts = within(section())
      .getAllByRole("listitem")
      .map((item) => item.textContent);
    expect(counts).toEqual([
      "2 comptes créés, sans rôle",
      "1 compte mis à jour",
      "Aucun compte désactivé",
      "1 identité de compte local rétablie dans le fournisseur",
      "1 compte local retiré du fournisseur",
      "2 signalés, laissés tels quels",
    ]);
    const toggle = screen.getByRole("button", { name: "Détails de la dernière lecture" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    const shown = await details();
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveAttribute("aria-controls", shown.id);
    const skipped = within(within(shown).getByRole("region", { name: "Laissés tels quels" }))
      .getAllByRole("listitem")
      .map((item) => [...item.querySelectorAll("p")].map((line) => line.textContent));
    expect(skipped).toEqual([
      [
        "Dominique BernardCompte Waterfall",
        "Adresse : dominique.bernard@example.com",
        "Au moins un compte actif doit garder les permissions d’administration.",
      ],
      [
        "Hugo GarnierPersonne du fournisseur d’identité",
        "Identifiant chez le fournisseur : 5b0c8e2a-3f6d-4a1e-9c47-2d8f1e6a7b90",
        "Le fournisseur d’identité ne tient aucune adresse pour cette personne.",
      ],
    ]);
    const removed = within(shown).getByRole("region", {
      name: "Comptes locaux retirés du fournisseur d’identité",
    });
    expect(within(removed).getByRole("listitem").textContent).toBe(
      "jeanne.montgolfier@example.com",
    );
    await expectAccessible(container);

    await userEvent.click(toggle);
    expect(screen.queryByRole("region", { name: "Détails de la dernière lecture" })).toBeNull();
  });

  it("names an account anonymised since by the neutral label, never by a name nor an address, and a person the provider gives no name [WF-ADM-0060-A]", async () => {
    serve({});
    const flagged = report("identity_sync_report_flagged");
    const [administrator, person] = flagged.skipped;
    if (administrator === undefined || person === undefined) {
      throw new Error("the example reports an account and a person");
    }
    // The same report read after the account was anonymised: its names and its address null, as
    // the API gives them; the person as a provider that holds no name gives her.
    const anonymised = { ...administrator, last_name: null, first_name: null, email: null };
    open({ ...flagged, skipped: [anonymised, { ...person, last_name: "", first_name: "" }] });
    const shown = await details();
    const [account, unnamed] = within(shown).getAllByRole("listitem");
    expect(account?.querySelector("[data-anonymized]")?.textContent).toBe("Compte anonymisé");
    expect(account?.textContent).not.toMatch(/Bernard|Dominique|@/);
    expect(unnamed?.querySelector("p")?.textContent).toBe(
      "Sans nom chez le fournisseurPersonne du fournisseur d’identité",
    );
  });

  it("says nothing was left nor removed when the reading reports nothing", async () => {
    serve({});
    open(report("identity_sync_report"));
    const shown = await details();
    expect(within(shown).getByText("Rien n’a été laissé tel quel.")).toBeVisible();
    expect(within(shown).getByText("Aucun compte local retiré.")).toBeVisible();
  });

  it.each([
    [
      { problem: { code: "PERMISSION_MISSING", status: 403 } } as const,
      "Vous n’avez pas la permission nécessaire.",
    ],
    [
      { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } } as const,
      "Un composant du service est indisponible.",
    ],
  ])(
    "tells a reading refused by the catalogue, and follows no task: %o",
    async (answer, sentence) => {
      const client = serve({ [START]: answer });
      open(undefined);
      await userEvent.click(screen.getByRole("button", { name: "Lire les comptes" }));
      expect(within(section()).getByRole("alert").textContent).toContain(sentence);
      expect(screen.queryByText("En attente")).toBeNull();
      expect(client.calls.map((call) => call.route)).toEqual([START]);
    },
  );

  it("offers no reading to a session that may not modify the accounts", () => {
    serve({});
    open(undefined, false);
    expect(within(section()).queryByRole("button")).toBeNull();
    expect(
      within(section()).getByText("Aucune lecture des comptes n’a encore abouti."),
    ).toBeVisible();
  });
});
