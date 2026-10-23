// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  type FakeTiming,
  fakeClient,
  held,
} from "@/test/fixtures";

import { GeneratePlanning } from "./generate-planning";
import { ProjectStart } from "./project-start";
import { keepFolded } from "./start-fold";
import { startOffers } from "./start-offers";

// The server of Next, as far as the encart needs it: the fake back behind serverClient, and the
// router that leads the screen.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => `/projects/${PROJECT}`,
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000103";
const START = `/projects/${PROJECT}`;
const BREAKDOWN = `${START}/settings?start=skeleton`;
const PLANNING = `${START}/revisions/${REVISION}/planning`;
const UPLOAD = "POST /file-uploads";
const OPEN = "POST /projects/{project_id}/imports";
const SKELETON = "POST /projects/{project_id}/revisions/{revision_id}/skeleton";
const TASK = "GET /tasks/{task_id}";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing?: FakeTiming): FakeClient {
  const client = fakeClient(answers, timing);
  server.client = client;
  return client;
}

/** Render a part of the page within the shell that follows the tasks, in French. */
function open(part: ReactNode) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>{part}</main>
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

/** What the encart offers for a revision and a project of the contract. */
function offered(revision = "revision_without_tasks", project = "project") {
  const offers = startOffers(example(project) as Project, example(revision) as Revision);
  if (offers === undefined) {
    throw new Error(`the encart is not offered on ${revision}`);
  }
  return offers;
}

/** The encart, as the page renders it. */
function encart(revision = "revision_without_tasks", project = "project") {
  return (
    <ProjectStart
      projectId={PROJECT}
      offers={offered(revision, project)}
      breakdownHref={BREAKDOWN}
      start={START}
    />
  );
}

beforeEach(() => {
  router.push.mockClear();
  router.refresh.mockClear();
  window.sessionStorage.clear();
  keepFolded(PROJECT, false);
  window.history.replaceState(null, "", START);
});

describe("what the page offers to start the planning", () => {
  it("offers it while the revision lists the skeleton and the main structure has no task [WF-PRJ-0030-A]", () => {
    expect(
      startOffers(example("project") as Project, example("revision_without_tasks") as Revision),
    ).toMatchObject({ skeleton: { is_available: true }, planningImport: { is_available: true } });
  });

  it("no longer offers it once the main structure bears a task, which the server says [WF-PRJ-0030-A]", () => {
    const revision = example("revision") as Revision;
    const skeleton = revision.available_commands.find((c) => c.command === "generate_skeleton");
    expect(skeleton?.missing_conditions).toContain("main_structure_without_tasks");
    expect(startOffers(example("project") as Project, revision)).toBeUndefined();
  });

  it("offers nothing without a revision in progress, or to a session the revision does not list the skeleton to", () => {
    expect(startOffers(example("project") as Project, undefined)).toBeUndefined();
    expect(
      startOffers(example("project") as Project, example("revision_reader") as Revision),
    ).toBeUndefined();
  });
});

describe("the encart « Démarrer le projet »", () => {
  it("offers the three choices, the first leading to the work breakdown in entry", async () => {
    serve({});
    const { container } = open(encart());
    const section = screen.getByRole("region", { name: "Démarrer le projet" });
    expect(
      within(section).getByRole("link", { name: "Planning automatique depuis le lotissement" }),
    ).toHaveAttribute("href", BREAKDOWN);
    expect(
      within(section).getByRole("button", { name: "Importer un fichier MS Project" }),
    ).toBeVisible();
    expect(within(section).getByRole("button", { name: "Plus tard" })).toBeVisible();
    await expectAccessible(container);
  });

  it("says what the skeleton lacks when the server lists it unavailable, and leads nowhere", () => {
    serve({});
    const unavailable = {
      skeleton: {
        command: "generate_skeleton" as const,
        is_available: false,
        missing_conditions: ["no_background_task_running" as const],
      },
      planningImport: undefined,
    };
    open(
      <ProjectStart
        projectId={PROJECT}
        offers={unavailable}
        breakdownHref={BREAKDOWN}
        start={START}
      />,
    );
    const command = screen.getByRole("button", {
      name: "Planning automatique depuis le lotissement",
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(/^Condition non remplie\s: /);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("button", { name: "Importer un fichier MS Project" })).toBeNull();
  });

  it("folds on « Plus tard », keeps the fold for the session, and unfolds from the button that stays", async () => {
    serve({});
    const { unmount } = open(encart());
    await userEvent.click(screen.getByRole("button", { name: "Plus tard" }));
    expect(screen.queryByRole("region", { name: "Démarrer le projet" })).toBeNull();
    const reopen = screen.getByRole("button", { name: "Démarrer le projet" });
    expect(reopen).toHaveAttribute("aria-expanded", "false");
    expect(reopen).toHaveFocus();
    // The page shown again in the same session finds it folded.
    unmount();
    open(encart());
    expect(screen.queryByRole("region", { name: "Démarrer le projet" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Démarrer le projet" }));
    const section = screen.getByRole("region", { name: "Démarrer le projet" });
    expect(within(section).getByRole("heading", { name: "Démarrer le projet" })).toHaveFocus();
  });

  it("opens the drop zone from « Importer un fichier MS Project », and closes it on « Plus tard »", async () => {
    serve({});
    open(encart());
    const command = screen.getByRole("button", { name: "Importer un fichier MS Project" });
    expect(command).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(command);
    expect(command).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("group", { name: "Zone de dépôt du fichier MS Project" }),
    ).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Plus tard" }));
    expect(screen.queryByRole("group", { name: "Zone de dépôt du fichier MS Project" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Démarrer le projet" })).toBeNull();
    // Unfolded again, the zone is closed, as it was left.
    await userEvent.click(screen.getByRole("button", { name: "Démarrer le projet" }));
    expect(screen.queryByRole("group", { name: "Zone de dépôt du fichier MS Project" })).toBeNull();
  });

  it("keeps the fold in memory when the browser refuses the storage of the tab", async () => {
    serve({});
    const refused = () => {
      throw new DOMException("denied", "SecurityError");
    };
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(refused);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(refused);
    try {
      const { unmount } = open(encart());
      await userEvent.click(screen.getByRole("button", { name: "Plus tard" }));
      expect(screen.queryByRole("region", { name: "Démarrer le projet" })).toBeNull();
      unmount();
      open(encart());
      expect(screen.queryByRole("region", { name: "Démarrer le projet" })).toBeNull();
      expect(screen.getByRole("button", { name: "Démarrer le projet" })).toBeVisible();
    } finally {
      vi.restoreAllMocks();
    }
  });
});

describe("the drop zone", () => {
  /** The encart with its drop zone open, and the fake back serving the import. */
  async function zone(answers: FakeAnswers = {}, timing?: FakeTiming) {
    const client = serve(answers, timing);
    const view = open(encart());
    await userEvent.click(screen.getByRole("button", { name: "Importer un fichier MS Project" }));
    const group = screen.getByRole("group", { name: "Zone de dépôt du fichier MS Project" });
    return { client, group, view };
  }

  const IMPORTED = {
    [UPLOAD]: { example: "file_upload", status: 201 },
    [OPEN]: { example: "import_analysing", status: 202 },
    [TASK]: "task_running",
  } as const satisfies FakeAnswers;

  it("is announced: named, described by what it takes, with a button that opens the selector", async () => {
    const { group, view } = await zone();
    expect(group).toHaveAccessibleDescription(/Glissez un fichier \.xml ici, ou choisissez-le/);
    const choose = within(group).getByRole("button", { name: "Choisir un fichier" });
    const selector = vi.spyOn(HTMLInputElement.prototype, "click");
    await userEvent.click(choose);
    expect(selector).toHaveBeenCalledOnce();
    selector.mockRestore();
    await expectAccessible(view.container);
  });

  it("sends a file chosen as an import of the schedule, follows its analysis, and shows its report", async () => {
    const { client, group } = await zone(IMPORTED);
    await userEvent.upload(
      within(group).getByLabelText("Fichier MS Project (.xml)"),
      new File(["<Project/>"], "planning.xml", { type: "text/xml" }),
    );
    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith(
        `${START}?import=01926f3a-7c00-7000-8000-000000000a11`,
      );
    });
    expect(client.calls.slice(0, 2).map((call) => call.route)).toEqual([UPLOAD, OPEN]);
    expect(client.calls[1]?.body).toMatchObject({ kind: "ms_project_schedule" });
  });

  it("sends a file dropped on the zone as it sends a file chosen", async () => {
    const { client, group } = await zone(IMPORTED);
    const file = new File(["<Project/>"], "planning.XML", { type: "text/xml" });
    fireEvent.dragOver(group, { dataTransfer: { files: [file] } });
    fireEvent.drop(group, { dataTransfer: { files: [file] } });
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toContain(OPEN);
    });
  });

  it("says it is sending, says a file dropped meanwhile is not taken, and takes no other once one is sent", async () => {
    const hold = held();
    const { client, group } = await zone(IMPORTED, hold.timing);
    const first = new File(["<Project/>"], "planning.xml", { type: "text/xml" });
    fireEvent.drop(group, { dataTransfer: { files: [first] } });
    expect(await within(group).findByRole("status")).toHaveTextContent(
      "Envoi de « planning.xml »…",
    );
    expect(group).toHaveAttribute("aria-busy", "true");
    fireEvent.drop(group, { dataTransfer: { files: [new File(["x"], "autre.xml")] } });
    expect(within(group).getByRole("alert")).toHaveTextContent("Un envoi est en cours");
    hold.release();
    await waitFor(() => {
      expect(router.push).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(within(group).getByRole("status")).toHaveTextContent("« planning.xml » est envoyé");
    });
    expect(within(group).queryByRole("alert")).toBeNull();
    const sent = client.calls.length;
    fireEvent.drop(group, { dataTransfer: { files: [new File(["x"], "autre.xml")] } });
    expect(client.calls).toHaveLength(sent);
    expect(within(group).getByRole("button", { name: "Choisir un fichier" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("stays highlighted while a file is dragged over a child of the zone, counted by its entries and its exits, and is not once it has left", async () => {
    const { group } = await zone();
    const child = within(group).getByRole("button", { name: "Choisir un fichier" });
    // Firefox gives a leave no `relatedTarget`: the drag is followed by what entered and left.
    fireEvent.dragEnter(group);
    expect(group.className).toContain("bg-accent");
    fireEvent.dragEnter(child);
    fireEvent.dragLeave(group);
    expect(group.className).toContain("bg-accent");
    fireEvent.dragLeave(child);
    expect(group.className).not.toContain("bg-accent");
    // A drop ends the drag, whatever was entered: the next drag starts from nothing.
    fireEvent.dragEnter(group);
    fireEvent.dragEnter(child);
    fireEvent.drop(group, { dataTransfer: { files: [] } });
    expect(group.className).not.toContain("bg-accent");
    fireEvent.dragEnter(group);
    fireEvent.dragLeave(group);
    expect(group.className).not.toContain("bg-accent");
  });

  it("takes another file once the task that analyses the one sent has not succeeded", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      // The contract has no failed analysis of the task the import opens: the follow-up of the task
      // is interrupted (404), an end like a failure for the zone, whatever the task's own status.
      const { client, group } = await zone({
        ...IMPORTED,
        [TASK]: { problem: { code: "NOT_FOUND", status: 404 } },
      });
      fireEvent.drop(group, {
        dataTransfer: { files: [new File(["<Project/>"], "planning.xml", { type: "text/xml" })] },
      });
      await waitFor(() => {
        expect(within(group).getByRole("status")).toHaveTextContent("« planning.xml » est envoyé");
      });
      const choose = within(group).getByRole("button", { name: "Choisir un fichier" });
      expect(choose).toHaveAttribute("aria-disabled", "true");
      await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
      await waitFor(() => {
        expect(within(group).queryByRole("status")).toBeNull();
      });
      expect(choose).not.toHaveAttribute("aria-disabled");
      const sent = client.calls.filter((call) => call.route === OPEN).length;
      fireEvent.drop(group, {
        dataTransfer: { files: [new File(["<Project/>"], "autre.xml", { type: "text/xml" })] },
      });
      await waitFor(() => {
        expect(client.calls.filter((call) => call.route === OPEN)).toHaveLength(sent + 1);
      });
    } finally {
      vi.useRealTimers();
    }
  });

  it("checks the type of the file before sending anything, and says so", async () => {
    const { client, group } = await zone();
    const reject = userEvent.setup({ applyAccept: false });
    await reject.upload(
      within(group).getByLabelText("Fichier MS Project (.xml)"),
      new File(["x"], "planning.mpp"),
    );
    expect(within(group).getByRole("alert")).toHaveTextContent("Ce n’est pas un fichier .xml");
    expect(client.calls).toEqual([]);
  });

  it("refuses at once a file larger than an import takes", async () => {
    const { client, group } = await zone();
    const large = new File(["x"], "planning.xml");
    Object.defineProperty(large, "size", { value: 10 * 1024 * 1024 + 1 });
    fireEvent.drop(group, { dataTransfer: { files: [large] } });
    expect(within(group).getByRole("alert")).toHaveTextContent("dépasse 10 Mio");
    expect(client.calls).toEqual([]);
  });

  it("tells a refusal of the deposit under the zone", async () => {
    const { group } = await zone({
      [UPLOAD]: { problem: { code: "FILE_TOO_LARGE", status: 413 } },
    });
    await userEvent.upload(
      within(group).getByLabelText("Fichier MS Project (.xml)"),
      new File(["x"], "planning.xml"),
    );
    await waitFor(() => {
      expect(within(group).getByRole("alert")).toHaveTextContent(
        CATALOGUES.fr.errors.FILE_TOO_LARGE,
      );
    });
    expect(router.push).not.toHaveBeenCalled();
  });
});

describe("« Engendrer le planning »", () => {
  /** The command, as the revision without tasks lists it. */
  function generate(revision = "revision_without_tasks") {
    const skeleton = (example(revision) as Revision).available_commands.find(
      (offer) => offer.command === "generate_skeleton",
    );
    if (skeleton === undefined) {
      throw new Error("the revision does not list the skeleton");
    }
    return (
      <GeneratePlanning
        projectId={PROJECT}
        revisionId={REVISION}
        offer={skeleton}
        planningHref={PLANNING}
      />
    );
  }

  // What the generation produces (a summary per work package and per post, their two end milestones) is
  // the back's: the front sends the command and leads to the grid, which this test carries.
  it("generates the planning on the revision, reads the page anew, and leads to the grid", async () => {
    const client = serve({ [SKELETON]: { example: "skeleton_generated", status: 201 } });
    open(generate());
    await userEvent.click(screen.getByRole("button", { name: "Engendrer le planning" }));
    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith(PLANNING);
    });
    expect(client.calls.map((call) => call.route)).toEqual([SKELETON]);
    expect(client.calls[0]?.path).toBe(`${START}/revisions/${REVISION}/skeleton`);
    expect(router.refresh).toHaveBeenCalled();
  });

  it("reads the page anew after a conflict, tells it, and does not lead to the grid", async () => {
    serve({
      [SKELETON]: {
        problem: {
          ...(example("skeleton_structure_not_empty") as components["schemas"]["Problem"]),
          status: 409 as const,
        },
      },
    });
    open(generate());
    await userEvent.click(screen.getByRole("button", { name: "Engendrer le planning" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeVisible();
    });
    expect(router.refresh).toHaveBeenCalled();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("is unavailable, naming its condition, once the structure bears a task, and asks nothing [WF-PRJ-0030-A]", async () => {
    const client = serve({});
    open(generate("revision"));
    const command = screen.getByRole("button", { name: "Engendrer le planning" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(/^Condition non remplie\s: /);
    await userEvent.click(command);
    expect(client.calls).toEqual([]);
    expect(router.push).not.toHaveBeenCalled();
  });
});
