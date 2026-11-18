// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, renderHook, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode, useTransition } from "react";
import { beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { decode, type Outcome } from "@/api/problem";
import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";
import { useNavigationHold } from "@/components/shell/navigation-hold";
import { SESSION_LOST_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { holdReading, Reading, releaseReading } from "@/test/held-reading";
import { atCommit } from "@/test/committed";
import { example, fakeClient, held, type Problem } from "@/test/fixtures";
import { browserOffline, browserOnline } from "@/test/offline";

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
  return (
    <RevisionCommands
      revision={example(name) as Revision}
      context={{
        projectId: PROJECT,
        revisionId: REVISION,
        revisionInPath: true,
        parameters: new URLSearchParams(),
      }}
    />
  );
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

/**
 * Another async action of the page — a dialog that writes, a long command —, run in a transition until
 * the test settles it: React 19 gives every async action under way one lane (`currentEntangledLane`).
 */
function OtherAction({ until }: { readonly until: Promise<void> }) {
  const [pending, startTransition] = useTransition();
  return (
    <button
      type="button"
      aria-busy={pending}
      onClick={() => {
        startTransition(async () => {
          await until;
        });
      }}
    >
      other
    </button>
  );
}

/** A refusal of the API, as the decoder hands it to a command. */
function refusal(kind: "conflict" | "stale", problem: Problem): Outcome<unknown> {
  const id = problem.params?.conflicting_object_id;
  return { kind, problem, conflictingObjectId: typeof id === "string" ? id : null };
}

beforeEach(() => {
  // Reset, not cleared: a test makes it read the page anew (US-2240).
  router.refresh.mockReset();
});

beforeEach(browserOffline);

describe("a command of a screen", () => {
  it("on a project in pricing, presents completion unavailable, naming the condition it lacks, which its tooltip opens on the focus of the keyboard [WF-IHM-0090-A]", async () => {
    const { container } = french(
      <LifecycleCommands project={example("project_pricing") as Project} />,
    );

    const complete = screen.getByRole("button", { name: "Terminer le projet" });
    expect(complete).toHaveAttribute("aria-disabled", "true");
    expect(complete).toHaveAccessibleDescription("Condition non remplie\u00A0: projet en cours.");
    // The text that names it is not written under the button: it is read in the tooltip.
    const unmet = document.getElementById(complete.getAttribute("aria-describedby") ?? "");
    expect(unmet).not.toBeVisible();
    await userEvent.tab();
    expect(complete).toHaveFocus();
    await screen.findByRole("tooltip");
    expect(document.querySelector("[data-slot=tooltip-content]")).toHaveTextContent(
      "projet en cours",
    );
    // The commands it may take now are offered.
    expect(screen.getByRole("button", { name: "Déclarer le projet perdu" })).not.toHaveAttribute(
      "aria-disabled",
    );
    await expectAccessible(container);
  });

  it("lists the commands in the order of the server, within a region named for them, its exports left to the screen of the exchanges and its entries and its skeleton to their grids", () => {
    french(revisionCommands("revision"));
    const region = screen.getByRole("region", { name: "Commandes" });
    // The declaration of a risk, which a main structure without task forbids (EP-14/L42s), is a
    // link to the screen of the risks (#1438).
    expect(
      within(region)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(["Déclarer un risque"]);
    expect(
      within(region)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual([
      "Préparer un avenant",
      "Appliquer la mise à jour des taux",
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
    // The declaration of a risk is a link, drawn like the buttons around it.
    const buttons = [...screen.getAllByRole("button"), ...screen.getAllByRole("link")];
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

  it("is described by the note of the write under way and by the conditions it lacks, both elements shown", () => {
    french(
      <Command
        offer={{ is_available: false, missing_conditions: ["project_in_progress"] }}
        label="Terminer le projet"
        help="Ce que la commande fait."
        icon={commandIcon(PROJECT_COMMAND_ICONS.complete)}
        writing
      />,
    );
    const complete = screen.getByRole("button", { name: "Terminer le projet" });
    const ids = (complete.getAttribute("aria-describedby") ?? "").split(" ");
    expect(ids).toHaveLength(2);
    const described = ids.map((id) => document.getElementById(id)?.textContent);
    expect(described[0]).toMatch(/\S/);
    expect(described[1]).toContain("projet en cours");
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

  it("tells the condition an unavailable command lacks in the region of the refusals when pressed, and not before [WF-IHM-0090-A]", async () => {
    french(
      <Command
        offer={{ is_available: false, missing_conditions: ["project_in_progress"] }}
        label="Terminer le projet"
        help="Ce que la commande fait."
        icon={commandIcon(PROJECT_COMMAND_ICONS.complete)}
      />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    expect(screen.getByRole("alert")).toHaveTextContent("projet en cours");
  });

  it("says what it does in its tooltip, and describes the button with the conditions it lacks [WF-IHM-0090-A]", async () => {
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
    // The hidden text of the conditions describes the button; the tooltip, open, adds its help.
    expect(complete).toHaveAccessibleDescription(
      "Condition non remplie\u00A0: projet en cours. Termine le projet, après confirmation.",
    );
  });

  it("forgets the refusal of a press once the command is available, and does not tell it again when it is not [WF-IHM-0090-A]", async () => {
    const unavailable = {
      is_available: false,
      missing_conditions: ["project_in_progress"],
    } as const;
    const available = { is_available: true, missing_conditions: [] } as const;
    const command = (offer: typeof available | typeof unavailable) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <Command
          offer={offer}
          label="Terminer le projet"
          help="Ce que la commande fait."
          icon={commandIcon(PROJECT_COMMAND_ICONS.complete)}
        />
      </NextIntlClientProvider>
    );
    const { rerender } = render(command(unavailable));
    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    rerender(command(available));
    expect(screen.queryByRole("alert")).toBeNull();
    rerender(command(unavailable));
    expect(screen.queryByRole("alert")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/Condition non remplie/);
  });

  it("leads « Déclarer un risque », available, to the screen of the risks of the revision, which its tooltip says [WF-IHM-0090-A]", async () => {
    french(revisionCommands("revision"));
    const link = screen.getByRole("link", { name: "Déclarer un risque" });
    expect(link).toHaveAttribute("href", `/projects/${PROJECT}/revisions/${REVISION}/risks`);
    await userEvent.hover(link);
    await screen.findByRole("tooltip");
    expect(document.querySelector("[data-slot=tooltip-content]")).toHaveTextContent(
      "Mène à l’écran des risques de la révision, où « Identifier un risque » s’offre.",
    );
  });

  it("presents « Déclarer un risque », unavailable, as a command that names what it lacks and leads nowhere [WF-IHM-0090-A]", async () => {
    french(revisionCommands("revision_without_tasks"));
    expect(screen.queryByRole("link", { name: "Déclarer un risque" })).toBeNull();
    const command = screen.getByRole("button", { name: "Déclarer un risque" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(/Condition non remplie/);
    await userEvent.click(command);
    expect(screen.getByRole("alert")).toHaveTextContent(/Condition non remplie/);
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

  it("tells its outcome and is no longer busy while another async action of the page still runs", async () => {
    const answer = held();
    const conflict = refusal("conflict", { code: "STATE_FORBIDS_OPERATION", status: 409 });
    const { container } = french(
      <>
        <OtherAction until={answer.until} />
        {available(() => Promise.resolve(conflict))}
      </>,
    );
    const other = screen.getByRole("button", { name: "other" });
    await userEvent.click(other);
    expect(other).toHaveAttribute("aria-busy", "true");

    // Busy no more in the commit that tells the outcome, which waits not for the other action: its
    // state lifted with the answer, never by a transition the other one holds (#1484).
    const command = screen.getByRole("button", { name: "Terminer le projet" });
    const busyWhenTold = atCommit(
      container,
      () => screen.queryByRole("alert") !== null,
      () => command.getAttribute("aria-busy"),
    );
    await userEvent.click(command);

    await screen.findByRole("alert");
    expect(busyWhenTold.stop()).toEqual(["false"]);
    expect(other).toHaveAttribute("aria-busy", "true");
    await act(async () => {
      answer.release();
      await answer.until;
    });
    expect(other).toHaveAttribute("aria-busy", "false");
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

  it("says the write may have been done, and holds the command until the screen is read anew, when the browser lost its server action while online [WF-REV-0010-A]", async () => {
    onTestFinished(browserOnline());
    holdReading(router.refresh);
    const action = vi.fn(() => Promise.reject(new TypeError("Failed to fetch")));
    french(<Reading>{available(action)}</Reading>);
    const command = screen.getByRole("button", { name: "Terminer le projet" });
    await userEvent.click(command);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("a pu aboutir");
    expect(alert).not.toHaveTextContent("injoignable");
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(action).toHaveBeenCalledOnce();

    await act(async () => {
      releaseReading();
      await Promise.resolve();
    });
    expect(command).not.toHaveAttribute("aria-disabled");
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
      "Le service est injoignable\u202F; réessayez dans un instant.",
    );
  });

  it("waits, pressed again, until the screen has been read anew after a write whose connection was lost once sent (US-2240)", async () => {
    // The page as Next reads it anew: the refresh a transition that stays pending until the server
    // answers — here until the test lets it go (`held-reading.tsx`).
    holdReading(router.refresh);
    const action = vi.fn(() =>
      Promise.resolve<Outcome<unknown>>({ kind: "unreachable", sent: true }),
    );
    french(<Reading>{available(action)}</Reading>);
    const command = screen.getByRole("button", { name: "Terminer le projet" });
    await userEvent.click(command);

    expect(await screen.findByRole("alert")).toHaveTextContent("l’opération a pu aboutir");
    expect(router.refresh).toHaveBeenCalledOnce();
    // The screen not yet read anew: the command waits, and a press runs nothing.
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("status")).toHaveTextContent("Relecture de l’écran…");
    await userEvent.click(command);
    expect(action).toHaveBeenCalledOnce();

    // The screen read anew: the command is given back, and the reading said no more.
    await act(async () => {
      releaseReading();
      await Promise.resolve();
    });
    expect(command).toHaveAttribute("aria-busy", "false");
    expect(command).not.toHaveAttribute("aria-disabled");
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    await userEvent.click(command);
    expect(action).toHaveBeenCalledTimes(2);
  });

  it("says nothing of a success", async () => {
    const action = vi.fn(() => Promise.resolve<Outcome<unknown>>({ kind: "done", data: null }));
    french(available(action));
    await userEvent.click(screen.getByRole("button", { name: "Terminer le projet" }));
    expect(action).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
