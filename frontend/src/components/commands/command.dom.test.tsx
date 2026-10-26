// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, renderHook, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { decode, type Outcome } from "@/api/problem";
import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";
import { useNavigationHold } from "@/components/shell/navigation-hold";
import { SESSION_LOST_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { atCommit } from "@/test/committed";
import { example, fakeClient, type Problem } from "@/test/fixtures";

import { Command } from "./command";
import { commandIcon, PROJECT_COMMAND_ICONS, REVISION_COMMAND_ICONS } from "./icons";
import { LifecycleCommands, RevisionCommands } from "./object-commands";
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
      help="Ce que la commande fait."
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

describe("a command of a screen", () => {
  it("on a project in pricing, presents completion unavailable, naming the condition it lacks [WF-IHM-0090-A]", async () => {
    const { container } = french(
      <LifecycleCommands project={example("project_pricing") as Project} />,
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

  it("lists the commands in the order of the server, within a region named for them, its exports left to the screen of the exchanges and its entries and its skeleton to their grids", () => {
    french(revisionCommands("revision"));
    const region = screen.getByRole("region", { name: "Commandes" });
    expect(
      within(region)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual([
      // The declaration of a risk, which a main structure without task forbids (EP-14/L42s).
      "Déclarer un risque",
      "Préparer un avenant",
      "Marquer la révision",
      "Abandonner la révision en cours",
    ]);
  });

  it("gives each command the icon of its kind, hidden from a screen reader beside its name", () => {
    french(
      <>
        <LifecycleCommands project={example("project") as Project} />
        {revisionCommands("revision")}
      </>,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(5);
    for (const button of buttons) {
      expect(button.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    }
    const icons = buttons.map((button) => button.querySelector("svg")?.getAttribute("class"));
    // One icon a kind: abandoning a project and abandoning a revision share theirs.
    expect(new Set(icons).size).toBe(buttons.length - 1);
  });

  it("names every condition a command lacks", () => {
    french(
      <Command
        offer={{
          is_available: false,
          missing_conditions: ["project_in_progress", "reference_revision_designated"],
        }}
        label="Déclarer la survenance d’un risque"
        help="Ce que la commande fait."
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
        help="Ce que la commande fait."
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

  it("says what it does in its tooltip, and the conditions it lacks beside its name", async () => {
    french(
      <Command
        offer={{ is_available: false, missing_conditions: ["project_in_progress"] }}
        label="Terminer le projet"
        help="Termine le projet, après confirmation."
        icon={commandIcon(PROJECT_COMMAND_ICONS.complete)}
      />,
    );
    const complete = screen.getByRole("button", { name: "Terminer le projet" });
    expect(complete).toHaveAttribute("aria-disabled", "true");
    await userEvent.hover(complete);
    await screen.findByRole("tooltip");
    expect(document.querySelector("[data-slot=tooltip-content]")).toHaveTextContent(
      "Termine le projet, après confirmation.",
    );
    expect(complete).not.toHaveAttribute("title");
    // The condition is said beside the command; the tooltip, open, adds its help to the description.
    expect(complete).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: projet en cours. Termine le projet, après confirmation.",
    );
  });

  it("does nothing when pressed before its operation is wired", async () => {
    french(revisionCommands("revision"));
    await userEvent.click(screen.getByRole("button", { name: "Déclarer un risque" }));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("form")).toBeNull();
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
          help="Ce que la commande fait."
          icon={commandIcon(REVISION_COMMAND_ICONS.mark)}
        />
      </>,
    );
    expect(screen.queryByRole("button", { name: "Marquer la révision" })).toBeNull();
    // The estimate, the one command left them, is offered by its grid: none is listed here.
    expect(screen.queryAllByRole("button")).toEqual([]);
  });

  it("is shown to a user with the permission to mark the revision", () => {
    french(revisionCommands("revision"));
    expect(screen.getByRole("button", { name: "Marquer la révision" })).not.toHaveAttribute(
      "aria-disabled",
    );
  });

  it("shows nothing when the user may exercise no command of the revision but its exports", () => {
    french(revisionCommands("revision_reader"));
    expect(screen.queryByRole("region", { name: "Commandes" })).toBeNull();
  });

  it("is offered for modification on a draft, and not on a marked revision [WF-IHM-0020-A]", () => {
    const draft = french(revisionCommands("revision"));
    // The draft carries amendment 2, not merged: another one opens all the same, several
    // coexisting (WF-REV-0100, #1211).
    for (const name of ["Préparer un avenant", "Abandonner la révision en cours"]) {
      expect(screen.getByRole("button", { name })).not.toHaveAttribute("aria-disabled");
    }
    draft.unmount();

    french(revisionCommands("revision_marked"));
    for (const name of ["Préparer un avenant", "Abandonner la révision en cours"]) {
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
    expect(screen.getByRole("button", { name: "Préparer un avenant" })).toHaveAttribute(
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
        help="Ce que la commande fait."
        icon={commandIcon(REVISION_COMMAND_ICONS.edit_planning)}
        action={write}
      />,
    );

    // Whether the command was still busy in the commit that told the refusal: the request over,
    // never while it holds a press (#1484).
    const command = screen.getByRole("button", { name: "Modifier le planning" });
    const busyWhenTold = atCommit(
      container,
      () => screen.queryByRole("alert") !== null,
      () => command.getAttribute("aria-busy"),
    );
    await userEvent.click(command);

    const alert = await screen.findByRole("alert");
    expect(busyWhenTold.stop()).toEqual(["false"]);
    expect(alert.textContent).toBe(
      "Seuls les contributeurs du projet peuvent le faire. " +
        "Condition non remplie\u00A0: être contributeur du projet.",
    );
    expect(client.calls).toHaveLength(1);
    await expectAccessible(container);
  });

  it("holds a navigation clicked while it runs, and drops it when the server refuses it: the refusal is told beside the command (#688)", async () => {
    const conflict = refusal("conflict", { code: "STATE_FORBIDS_OPERATION", status: 409 });
    let answer: (outcome: Outcome<unknown>) => void = () => undefined;
    renderHook(() => {
      useNavigationHold();
    });
    french(
      available(
        () =>
          new Promise((resolve) => {
            answer = resolve;
          }),
      ),
    );
    const followed = vi.fn((event: MouseEvent) => {
      event.preventDefault();
    });
    const link = document.createElement("a");
    link.href = "/portfolio";
    link.addEventListener("click", followed);
    document.body.append(link);

    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    fireEvent.pointerDown(link);
    link.click();
    await act(async () => {
      answer(conflict);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération.",
    );
    expect(followed).not.toHaveBeenCalled();
    link.remove();
  });

  it("says a session lost when its server action rejects with the digest of one, and offers the sign-in by a link", async () => {
    const lost = Object.assign(new Error("Server Components render"), {
      digest: SESSION_LOST_DIGEST,
    });
    french(available(() => Promise.reject(lost)));

    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(CATALOGUES.fr.errors.SESSION_REQUIRED);
    expect(within(alert).getByRole("link", { name: "Se connecter" })).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent(`/projects/${PROJECT}/lifecycle`)}`,
    );
  });

  it("says the service out of reach when the browser cannot reach its server action", async () => {
    french(available(() => Promise.reject(new TypeError("Failed to fetch"))));

    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));

    expect((await screen.findByRole("alert")).textContent).toBe(CATALOGUES.fr.outcome.unreachable);
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
