// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { decode, type Outcome } from "@/api/problem";
import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient, type Problem } from "@/test/fixtures";

import { Command } from "./command";
import { commandIcon, PROJECT_COMMAND_ICONS, REVISION_COMMAND_ICONS } from "./icons";
import { ProjectCommands, RevisionCommands } from "./object-commands";
import { findOffer } from "./offer";

// The router of Next, as far as a command needs it: the address it shows, and the refresh
// that reads the screen anew.
const router = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/lifecycle",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** Render in French, as the shell hands its texts to a screen. */
function french(children: ReactNode) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {children}
    </NextIntlClientProvider>,
  );
}

/** The commands of a revision of the contract. */
function revisionCommands(name: string) {
  return <RevisionCommands revision={example(name) as Revision} />;
}

/** A command the server offers now, whose action answers what the test says. */
function available(action: () => Promise<Outcome<unknown>>, names?: Record<string, string>) {
  return (
    <Command
      offer={{ is_available: true, missing_conditions: [] }}
      label="Terminer le projet"
      icon={commandIcon(PROJECT_COMMAND_ICONS.complete)}
      action={action}
      names={names}
    />
  );
}

/** A refusal of the API, as the decoder hands it to a command. */
function refusal(kind: "conflict" | "stale", problem: Problem): Outcome<unknown> {
  const id = problem.params?.conflicting_object_id;
  return { kind, problem, conflictingObjectId: typeof id === "string" ? id : null };
}

beforeEach(() => {
  router.refresh.mockClear();
});

describe("a command of a project", () => {
  it("on a project in pricing, presents completion unavailable, naming the condition it lacks [WF-IHM-0090-A]", async () => {
    const { container } = french(
      <ProjectCommands project={example("project_pricing") as Project} />,
    );

    const complete = screen.getByRole("button", { name: "Terminer le projet" });
    expect(complete).toHaveAttribute("aria-disabled", "true");
    expect(complete).toHaveAccessibleDescription("Condition non remplie\u00A0: projet en cours.");
    // The text that names it is shown beside the command, not only read out.
    const unmet = document.getElementById(complete.getAttribute("aria-describedby") ?? "");
    expect(unmet).toBeVisible();
    // The commands it may take now are offered.
    expect(screen.getByRole("button", { name: "Déclarer le projet perdu" })).not.toHaveAttribute(
      "aria-disabled",
    );
    await expectAccessible(container);
  });

  it("lists the commands in the order of the server, within a region named for them", () => {
    french(<ProjectCommands project={example("project") as Project} />);
    const region = screen.getByRole("region", { name: "Commandes" });
    expect(
      within(region)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual([
      "Modifier le projet",
      "Gérer les contributeurs",
      "Créer une révision",
      "Terminer le projet",
      "Déclarer le projet perdu",
      "Abandonner le projet",
      "Modifier les risques",
      "Déclarer la survenance d’un risque",
      "Importer les coûts réels",
      "Exclure des lignes de coût",
    ]);
  });

  it("gives each command the icon of its kind, hidden from a screen reader beside its name", () => {
    french(
      <>
        <ProjectCommands project={example("project") as Project} />
        {revisionCommands("revision")}
      </>,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(10);
    for (const button of buttons) {
      expect(button.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    }
    const icons = buttons.map((button) => button.querySelector("svg")?.getAttribute("class"));
    expect(new Set(icons).size).toBeGreaterThan(10);
  });

  it("names every condition a command lacks", () => {
    french(
      <Command
        offer={{
          is_available: false,
          missing_conditions: ["project_in_progress", "reference_revision_designated"],
        }}
        label="Déclarer la survenance d’un risque"
        icon={commandIcon(PROJECT_COMMAND_ICONS.declare_risk_occurrence)}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Déclarer la survenance d’un risque" }),
    ).toHaveAccessibleDescription(
      "Conditions non remplies\u00A0: projet en cours et révision de référence désignée.",
    );
  });

  it("does nothing when pressed unavailable: the server is not asked", async () => {
    const action = vi.fn(() => Promise.resolve<Outcome<unknown>>({ kind: "done", data: null }));
    french(
      <Command
        offer={{ is_available: false, missing_conditions: ["project_in_progress"] }}
        label="Terminer le projet"
        icon={commandIcon(PROJECT_COMMAND_ICONS.complete)}
        action={action}
      />,
    );
    const complete = screen.getByRole("button", { name: "Terminer le projet" });
    await userEvent.click(complete);
    complete.focus();
    await userEvent.keyboard("{Enter}");
    expect(action).not.toHaveBeenCalled();
    expect(complete).toHaveFocus();
  });

  it("does nothing when pressed before its operation is wired", async () => {
    french(<ProjectCommands project={example("project") as Project} />);
    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("a command of a revision", () => {
  it("is not shown to a user without the permission to mark the revision [WF-IHM-0090-A]", () => {
    const reader = example("revision_reader") as Revision;
    french(
      <>
        {revisionCommands("revision_estimator")}
        <Command
          offer={findOffer(reader.available_commands, "mark")}
          label="Marquer la révision"
          icon={commandIcon(REVISION_COMMAND_ICONS.mark)}
        />
      </>,
    );
    expect(screen.queryByRole("button", { name: "Marquer la révision" })).toBeNull();
    expect(screen.getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Modifier le devis",
    ]);
  });

  it("is shown to a user with the permission to mark the revision", () => {
    french(revisionCommands("revision"));
    expect(screen.getByRole("button", { name: "Marquer la révision" })).not.toHaveAttribute(
      "aria-disabled",
    );
  });

  it("shows nothing when the user may exercise no command of the revision", () => {
    french(revisionCommands("revision_reader"));
    expect(screen.queryByRole("region", { name: "Commandes" })).toBeNull();
  });

  it("is offered for modification on a draft, and not on a marked revision [WF-IHM-0020-A]", () => {
    const draft = french(revisionCommands("revision"));
    expect(screen.getByRole("button", { name: "Modifier le planning" })).not.toHaveAttribute(
      "aria-disabled",
    );
    draft.unmount();

    french(revisionCommands("revision_marked"));
    for (const name of [
      "Modifier le planning",
      "Modifier le devis",
      "Réestimer le reste à engager",
    ]) {
      const edit = screen.getByRole("button", { name });
      expect(edit).toHaveAttribute("aria-disabled", "true");
      expect(edit).toHaveAccessibleDescription(
        "Condition non remplie\u00A0: révision en cours d’élaboration.",
      );
    }
  });

  it("presents a second marking unavailable while the first runs, naming the treatment under way", () => {
    french(revisionCommands("revision_marking"));
    const mark = screen.getByRole("button", { name: "Marquer la révision" });
    expect(mark).toHaveAttribute("aria-disabled", "true");
    expect(mark).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: aucun traitement de fond en cours sur l’objet.",
    );
    expect(screen.getByRole("button", { name: "Modifier le planning" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });
});

describe("the outcome of a command", () => {
  it("names the condition when the server refuses an entry to a user who is not a contributor [WF-IHM-0090-A]", async () => {
    const client = fakeClient({
      "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task":
        {
          problem: {
            code: "NOT_CONTRIBUTOR",
            status: 403,
            params: { missing_condition: "is_contributor" },
          },
        },
    });
    const write = () =>
      decode(() =>
        client.PATCH(
          "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task",
          {
            params: {
              path: {
                project_id: PROJECT,
                revision_id: REVISION,
                structure_id: "01926f3a-7c00-7000-8000-000000000201",
                node_id: "01926f3a-7c00-7000-8000-000000000401",
              },
            },
            body: { label: "Études", lock_version: 3 },
          },
        ),
      );
    // Greyed out or not, a command is the server's to judge: its refusal is told.
    const { container } = french(
      <Command
        offer={{ is_available: true, missing_conditions: [] }}
        label="Modifier le planning"
        icon={commandIcon(REVISION_COMMAND_ICONS.edit_planning)}
        action={write}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Modifier le planning" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe(
      "Seuls les contributeurs du projet peuvent le faire. " +
        "Condition non remplie\u00A0: être contributeur du projet.",
    );
    expect(client.calls).toHaveLength(1);
    await expectAccessible(container);
  });

  it("explains a conflict, naming the object in conflict", async () => {
    const conflict = refusal("conflict", {
      code: "STATE_FORBIDS_OPERATION",
      status: 409,
      params: { conflicting_object_id: PROJECT },
    });
    french(available(() => Promise.resolve(conflict), { [PROJECT]: "Modernisation" }));

    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));

    const alert = await screen.findByRole("alert");
    expect([...alert.children].map((line) => line.textContent)).toEqual([
      "L’état actuel ne permet pas cette opération.",
      "Objet en conflit\u00A0: Modernisation.",
    ]);
  });

  it("explains a conflict without naming an object the screen does not know", async () => {
    const conflict = refusal("conflict", {
      code: "STATE_FORBIDS_OPERATION",
      status: 409,
      params: { conflicting_object_id: REVISION },
    });
    french(available(() => Promise.resolve(conflict), { [PROJECT]: "Modernisation" }));

    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "L’état actuel ne permet pas cette opération.",
    );
  });

  it("offers to reload an object changed since it was read, and reloads it", async () => {
    const stale = refusal("stale", { code: "STALE_LOCK_VERSION", status: 412 });
    french(available(() => Promise.resolve(stale)));

    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Quelqu’un a modifié cette donnée entre-temps");
    await userEvent.click(within(alert).getByRole("button", { name: "Recharger" }));

    expect(router.refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("leads to the sign-in page, which comes back to the screen, when the session is gone", async () => {
    const problem = { code: "SESSION_EXPIRED", status: 401 } as const;
    french(
      available(() => Promise.resolve({ kind: "signed_out", problem, conflictingObjectId: null })),
    );

    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByRole("link", { name: "Se connecter" })).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent(`/projects/${PROJECT}/lifecycle`)}`,
    );
  });

  it("says the API is out of reach", async () => {
    french(available(() => Promise.resolve({ kind: "unreachable" })));
    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Le service est injoignable ; réessayez dans un instant.",
    );
  });

  it("says nothing of a success", async () => {
    const action = vi.fn(() => Promise.resolve<Outcome<unknown>>({ kind: "done", data: null }));
    french(available(action));
    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    expect(action).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
