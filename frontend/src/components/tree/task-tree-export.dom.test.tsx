// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { Revision } from "@/components/context/read-only";
import { exportOffers } from "@/components/exchanges/offers";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { heldFrames } from "@/test/download-frames";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { closeTasks, tasksRegion } from "@/test/task-panel";

import { TaskTreeExport } from "./task-tree-export";

// The server of Next, as far as the export needs it: the fake back behind serverClient.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => `/projects/${PROJECT}/revisions/${REVISION}/task-tree`,
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const EXPORT = "POST /projects/{project_id}/exports";
const TASK = "GET /tasks/{task_id}";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** Render the command at a depth, within the shell that follows the tasks. */
function open(depth: number) {
  const offer = exportOffers(example("revision") as Revision).task_tree_image;
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>
          <TaskTreeExport projectId={PROJECT} revisionId={REVISION} depth={depth} offer={offer} />
        </main>
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

/** The hidden frames the image downloads by itself through. */
let frames: readonly HTMLIFrameElement[] = [];

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
  // The result of an export the tree asked for downloads by itself once made, by a hidden frame
  // (#3103): held, in the document, happy-dom loading no page in it (`download-frames.ts`).
  frames = heldFrames();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

/** The command. */
function command() {
  return screen.getByRole("button", { name: "Exporter l’image de l’arborescence de tâches" });
}

/** Press the command, and wait for the request to be answered: its task then runs. */
async function request() {
  const button = command();
  await userEvent.click(button);
  await waitFor(() => {
    expect(button.querySelector("[data-waiting]")).not.toBeNull();
  });
}

describe("the export of the image of the task tree", () => {
  it("asks the image at the level shown, then offers its download once drawn [WF-PLA-0120-A]", async () => {
    // L'export d'un planning de trois niveaux produit un fichier PNG.
    const client = serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_succeeded",
    });
    open(3);
    await request();
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [
        `/projects/${PROJECT}/exports`,
        { kind: "task_tree_image", revision_id: REVISION, depth: 3 },
      ],
    ]);
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    const download = await within(tasksRegion()).findByRole("link", {
      name: /^Télécharger le résultat/,
    });
    expect(download.getAttribute("href")).toMatch(/^\/tasks\/[^/]+\/result\?from=/);
  });

  it("downloads the image by itself once drawn, the tree still shown (#3103)", async () => {
    serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_succeeded",
    });
    open(3);
    await request();
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(frames).toHaveLength(1);
    });
    // By a hidden frame: the tree is not left.
    expect(frames[0]?.getAttribute("src")).toMatch(
      /^\/tasks\/01926f3a-7c00-7000-8000-000000000935\/result\?from=/,
    );
  });

  it("asks the first level at least, for a plan that has no summary [WF-PLA-0120-A]", async () => {
    const client = serve({ [EXPORT]: { example: "task_export_queued", status: 202 } });
    open(0);
    await request();
    expect(client.calls.map((call) => call.body)).toEqual([
      { kind: "task_tree_image", revision_id: REVISION, depth: 1 },
    ]);
  });

  it("tells an image beyond one hundred million pixels, and invites a shallower level [WF-PLA-0120-A]", async () => {
    // L'export d'une arborescence dont l'image dépasserait cent millions de pixels échoue, et
    // l'échec le dit.
    serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_tree_image_too_large",
    });
    open(4);
    await request();
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(tasksRegion()).toHaveTextContent(CATALOGUES.fr.errors.TASK_TREE_IMAGE_TOO_LARGE);
    });
  });

  it("waits, saying so, while its task runs, asks no second image, and is given back by its failure [WF-IHM-0080-A]", async () => {
    // The export of an image asked from a button that said nothing (#3103).
    const client = serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_tree_image_too_large",
    });
    open(4);
    await request();
    const button = command();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(button);
    const asked = () => client.calls.filter((call) => call.route === EXPORT);
    expect(asked()).toHaveLength(1);

    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    expect(within(tasksRegion()).getByText("Échouée")).toBeVisible();
    closeTasks();
    expect(button).toHaveAttribute("aria-busy", "false");
    expect(button).not.toHaveAttribute("aria-disabled");
    expect(button.querySelector("[data-waiting]")).toBeNull();
    await userEvent.click(button);
    await waitFor(() => {
      expect(asked()).toHaveLength(2);
    });
  });

  it("is absent where the revision does not list the command", () => {
    serve({});
    const revision = structuredClone(example("revision") as Revision);
    revision.available_commands = revision.available_commands.filter(
      (command) => command.command !== "export_task_tree_image",
    );
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <TaskTracker>
          <TaskTreeExport
            projectId={PROJECT}
            revisionId={REVISION}
            depth={2}
            offer={exportOffers(revision).task_tree_image}
          />
        </TaskTracker>
      </NextIntlClientProvider>,
    );
    expect(screen.queryByRole("button")).toBeNull();
  });
});
