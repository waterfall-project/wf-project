// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { atCommit } from "@/test/committed";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { tasksRegion } from "@/test/task-panel";

import { IdentityMenu, IdentitySync, type IdentitySyncReport } from "./identity-sync";

type IdentitySyncSchedule = components["schemas"]["IdentitySyncSchedule"];

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
function open(
  shown: IdentitySyncReport | undefined,
  startable = true,
  schedule: IdentitySyncSchedule = example("identity_sync_schedule") as IdentitySyncSchedule,
) {
  const tree = (given: IdentitySyncReport | undefined) => (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>
          <IdentitySync report={given} schedule={schedule} startable={startable} />
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
  it("gives the hand back as soon as the reading is queued, follows it to its end, and the user sees it ended [WF-ARC-0090-A]", async () => {
    // La lecture des comptes ne tient aucune requête au-delà de la création de la tâche, et
    // l'utilisateur en voit l'aboutissement : the command answers with the task queued, the
    // tracker reads it until it has succeeded, announces it, and offers to read the screen anew.
    const client = serve({
      [START]: { example: "identity_sync_queued", status: 202 },
      [TASK]: "identity_sync_succeeded",
    });
    open(report("identity_sync_report"));

    await userEvent.click(within(section()).getByRole("button", { name: "Lire les comptes" }));
    expect(client.calls.map((call) => call.route)).toEqual([START]);
    // Nothing of the screen is withheld while the worker reads.
    expect(document.querySelector("[aria-modal], [inert], :disabled")).toBeNull();
    const tasks = tasksRegion();
    expect(within(tasks).getByText("En attente")).toBeVisible();

    await tick();
    expect(client.calls.filter((call) => call.route === TASK).map((call) => call.path)).toEqual([
      "/tasks/01926f3a-7c00-7000-8000-000000000941",
    ]);
    expect(within(tasks).getByText("Réussie")).toBeVisible();
    expect(screen.getByRole("log").textContent).toBe(
      "Tâche terminée\u00A0: Lecture des comptes du fournisseur d’identité.",
    );
    // Its result is a report to read on the screen, not a file to download.
    expect(within(tasks).queryByRole("link", { name: /Télécharger/ })).toBeNull();
    await userEvent.click(within(tasks).getByRole("button", { name: "Recharger l’écran" }));
    expect(router.refresh).toHaveBeenCalledOnce();

    // No report is asserted: the contract serves none for that task, so the test proves the end of
    // the reading and the offer to read the screen anew, not the report that screen then shows (#984).
  });

  it("presents what the last reading did, the last administrator kept and reported, a person without an address named by her identifier at the provider, a person whose address an account holds named by that account, each by the motive of the catalogue [WF-ADM-0070-A]", async () => {
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
      "3 signalés, laissés tels quels",
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
        "Adresse\u00A0: dominique.bernard@example.com",
        "Au moins un compte actif doit garder les permissions d’administration.",
      ],
      [
        "Hugo GarnierPersonne du fournisseur d’identité",
        "Identifiant chez le fournisseur\u00A0: 5b0c8e2a-3f6d-4a1e-9c47-2d8f1e6a7b90",
        "Le fournisseur d’identité ne tient aucune adresse pour cette personne.",
      ],
      [
        "Personne du fournisseur d’identité",
        "Adresse portée par : Dominique Bernard",
        "Identifiant chez le fournisseur\u00A0: ef2f3c85-8bd7-4fec-bfa9-7f0a46f62620",
        "Cet élément existe déjà.",
      ],
    ]);
    // The person whose address an account holds keeps nothing of her own but her identifier: the
    // account is named, never the address it holds (#920).
    expect(skipped[2]?.filter((line) => line.includes("@"))).toEqual([]);
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

  it("names an account anonymised since by the neutral label, never by a name nor an address, the person whose address it held by her identifier, and a person the provider gives no name [WF-ADM-0060-A]", async () => {
    serve({});
    open(report("identity_sync_report_anonymized"));
    const shown = await details();
    const entries = within(within(shown).getByRole("region", { name: "Laissés tels quels" }))
      .getAllByRole("listitem")
      .map((item) => [...item.querySelectorAll("p")].map((line) => line.textContent));
    expect(entries).toEqual([
      ["Compte anonymiséCompte Waterfall", "Les données saisies ne sont pas valides."],
      [
        "Sans nom chez le fournisseurPersonne du fournisseur d’identité",
        "Adresse\u00A0: contact.chantier@example.com",
        "Identifiant chez le fournisseur\u00A0: 8e3f1c2a-6b4d-4f0e-a1c9-7d2e5b8f3a61",
        "Les données saisies ne sont pas valides.",
      ],
      [
        "Personne du fournisseur d’identité",
        "Adresse portée par : Compte anonymisé",
        "Identifiant chez le fournisseur\u00A0: c47a2e9b-1d5f-4b8c-9e3a-6f0d2c8b5e14",
        "Cet élément existe déjà.",
      ],
      [
        "Personne du fournisseur d’identité",
        "Identifiant chez le fournisseur\u00A0: 2f9d6b1e-8a3c-4e7f-b5d2-9c1a4e6f8b03",
        "Cet élément existe déjà.",
      ],
    ]);
    // The neutral label is the one rendering of an anonymised account, for the account left as it
    // was as for the one that held the address of a person.
    expect(
      [...shown.querySelectorAll("[data-anonymized]")].map((label) => label.textContent),
    ).toEqual(["Compte anonymisé", "Compte anonymisé"]);
    expect(shown.textContent).not.toMatch(/Moreau|Alix/);
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
      // Whether the command was still busy in the commit that told the refusal: the request over,
      // never while it holds a press (#1484).
      const start = screen.getByRole("button", { name: "Lire les comptes" });
      const busyWhenTold = atCommit(
        section(),
        () => within(section()).queryByRole("alert") !== null,
        () => start.getAttribute("aria-busy"),
      );
      await userEvent.click(start);
      expect((await within(section()).findByRole("alert")).textContent).toContain(sentence);
      expect(busyWhenTold.stop()).toEqual(["false"]);
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

/** The menu « ⋯ » of the reading, within the shell that follows the tasks. */
function menu(startable = true) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>
          <IdentityMenu
            report={undefined}
            schedule={example("identity_sync_schedule") as IdentitySyncSchedule}
            startable={startable}
          />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

/** The button « ⋯ » that opens the menu of the reading. */
function trigger() {
  return screen.getByRole("button", {
    name: "Lecture des comptes du fournisseur d’identité : état et commandes",
  });
}

/** The popover the menu opened. */
function popover() {
  return screen.getByRole("dialog", { name: "Lecture des comptes du fournisseur d’identité" });
}

describe("the menu « ⋯ » of the reading of the accounts", () => {
  it("hides the report, the command and the periodicity until it is opened, then gives them, with the state when no reading has ended [WF-ADM-0070-A]", async () => {
    serve({});
    menu();
    expect(screen.queryByRole("button", { name: "Lire les comptes" })).toBeNull();
    expect(screen.queryByText("Aucune lecture des comptes n’a encore abouti.")).toBeNull();
    await userEvent.click(trigger());
    expect(within(popover()).getByRole("button", { name: "Lire les comptes" })).toBeVisible();
    expect(
      within(popover()).getByText("Aucune lecture des comptes n’a encore abouti."),
    ).toBeVisible();
    expect(within(popover()).getByText("Périodicité de la lecture")).toBeVisible();
    await expectAccessible(document.body);
  });

  it("tells a refusal of the reading beside the menu, and keeps it when the menu is closed unread [US-1860]", async () => {
    serve({ [START]: { problem: { code: "PERMISSION_MISSING", status: 403 } } });
    menu();
    await userEvent.click(trigger());
    await userEvent.click(within(popover()).getByRole("button", { name: "Lire les comptes" }));
    const told = "Vous n’avez pas la permission nécessaire.";
    expect((await screen.findByRole("alert")).textContent).toContain(told);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("alert").textContent).toContain(told);
  });

  it("follows the task of a reading asked from the menu after the menu is closed [WF-ARC-0090-A]", async () => {
    const client = serve({
      [START]: { example: "identity_sync_queued", status: 202 },
      [TASK]: "identity_sync_succeeded",
    });
    menu();
    await userEvent.click(trigger());
    await userEvent.click(within(popover()).getByRole("button", { name: "Lire les comptes" }));
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    await tick();
    expect(client.calls.filter((call) => call.route === TASK)).toHaveLength(1);
    expect(within(tasksRegion()).getByText("Réussie")).toBeVisible();
  });

  it("keeps the dialog of the periodicity open, the focus in it, while the menu that opened it stays [WF-ADM-0070-A]", async () => {
    serve({});
    menu();
    await userEvent.click(trigger());
    await userEvent.click(
      within(popover()).getByRole("button", { name: "Modifier la périodicité" }),
    );
    const form = screen.getByRole("dialog", { name: "Modifier la périodicité" });
    expect(form).toBeVisible();
    expect(form.contains(document.activeElement)).toBe(true);
    // The menu stays: the dialog is not a click outside of it.
    expect(screen.getByRole("dialog", { name: "Lecture des comptes du fournisseur d’identité", hidden: true })).toBeInTheDocument();
  });
});
