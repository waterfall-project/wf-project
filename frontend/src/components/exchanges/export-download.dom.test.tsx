// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { Revision } from "@/components/context/read-only";
import { EndCards } from "@/components/tasks/end-cards";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { heldFrames, sendBack } from "@/test/download-frames";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { ExportForm } from "./export-form";
import { exportOffers } from "./offers";

// The result of an export, downloaded by itself once the task has succeeded while the screen that
// asked for it still shows — a criterion of US-2170 (#3103, decided by the author on 2026-11-13),
// which no requirement carries: the tests below cite none. The server of Next, as far as the export
// needs it.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => window.location.pathname,
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const EXCHANGES = `/projects/${PROJECT}/revisions/${REVISION}/exchanges`;
const EXPORTED = "01926f3a-7c00-7000-8000-000000000935";
const EXPORT = "POST /projects/{project_id}/exports";
const TASK = "GET /tasks/{task_id}";
const SHOWN = window.location.href;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The shell, with the request of an export on the screen while `shown`, and the cards. */
function shell(shown: boolean) {
  const offers = exportOffers(example("revision") as Revision);
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>
          {shown ? <ExportForm projectId={PROJECT} revisionId={REVISION} offers={offers} /> : null}
        </main>
        <EndCards />
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** Ask for the export, and wait for its task to be handed over. */
async function ask() {
  const form = screen.getByRole("form", { name: "Demander un export" });
  await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
  await waitFor(() => {
    expect(form).toHaveAttribute("aria-busy", "false");
  });
}

/** The links a click went on to, recorded — and stopped there: happy-dom follows no link. */
let followed: string[] = [];

/** Record the link a click went on to, and stop it there. */
function record(event: Event) {
  const link = event.target instanceof Element ? event.target.closest("a") : null;
  if (link !== null) {
    if (!event.defaultPrevented) {
      followed.push(link.getAttribute("href") ?? "");
    }
    event.preventDefault();
  }
}

/** The address of the result of the export, leaving from the screen of the exchanges. */
const RESULT = `/tasks/${EXPORTED}/result?from=${encodeURIComponent(EXCHANGES)}`;

/** How long a frame that downloads is kept (`FRAME_KEPT` of `result-download.tsx`): five minutes. */
const FRAME_KEPT = 5 * 60_000;

/** The hidden frames the result downloads by itself through. */
let frames: readonly HTMLIFrameElement[] = [];

beforeEach(() => {
  followed = [];
  frames = heldFrames();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
  window.history.replaceState(null, "", EXCHANGES);
  document.addEventListener("click", record);
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    this.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });
});

afterEach(() => {
  document.removeEventListener("click", record);
  vi.restoreAllMocks();
  window.history.replaceState(null, "", SHOWN);
  vi.useRealTimers();
});

/** The card of the end of the export. */
function exportCard() {
  return within(screen.getByRole("region", { name: "Aboutissements des tâches" })).getByRole(
    "group",
  );
}

describe("the result of an export", () => {
  it("is downloaded by itself once the task has succeeded, the screen that asked for it still open, read anew first, once, its card offering it no more (#3103)", async () => {
    const client = serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_succeeded",
    });
    render(shell(true));
    await ask();
    expect(frames).toEqual([]);
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(frames.map((frame) => frame.getAttribute("src"))).toEqual([RESULT]);
    });
    // A hidden frame, which runs no script and may download: no link leaves the screen.
    const [frame] = frames;
    expect(frame).toHaveAttribute("sandbox", "allow-downloads allow-same-origin");
    expect(frame).not.toBeVisible();
    expect(followed).toEqual([]);
    expect(window.location.pathname).toBe(EXCHANGES);
    // The read of the follow-up, then the read that checks the result is still there.
    const reads = () => client.calls.filter((call) => call.route === TASK);
    expect(reads()).toHaveLength(2);
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL * 3));
    expect(frames).toHaveLength(1);
    expect(reads()).toHaveLength(2);
    // Served once (WF-DAT-0120): the card keeps its sentence and its cross, and offers it no more.
    const card = exportCard();
    expect(card).toHaveTextContent(/^Tâche terminée\s: Export/);
    expect(within(card).queryByRole("link", { name: /^Télécharger/ })).toBeNull();
    expect(within(card).getByRole("button", { name: /^Fermer la carte/ })).toBeVisible();
  });

  it("keeps the hidden frame in the document five minutes, then takes it away, the download going on without it (#3298)", async () => {
    serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_succeeded",
    });
    render(shell(true));
    await ask();
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(frames).toHaveLength(1);
    });
    const [frame] = frames;
    expect(frame?.isConnected).toBe(true);
    await act(() => vi.advanceTimersByTimeAsync(FRAME_KEPT - POLL_INTERVAL));
    expect(frame?.isConnected).toBe(true);
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    expect(frame?.isConnected).toBe(false);
    // Taken away, it began no other download, and the screen stays.
    expect(frames).toHaveLength(1);
    expect(window.location.pathname).toBe(EXCHANGES);
  });

  it("leaves the screen as it is when the route refuses the file after the read, its card telling why (#3103)", async () => {
    serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_succeeded",
    });
    render(shell(true));
    await ask();
    // What the user chose meanwhile stays: the screen is neither left nor loaded again.
    const form = screen.getByRole("form", { name: "Demander un export" });
    const kinds = within(form).getByRole<HTMLSelectElement>("combobox", {
      name: "Fichier à exporter",
    });
    const chosen = within(kinds).getAllByRole<HTMLOptionElement>("option").at(-1)?.value ?? "";
    await userEvent.selectOptions(kinds, chosen);
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(frames).toHaveLength(1);
    });
    // The result expired between the read and the download (409): the route sends the frame to a
    // page with nothing in it, the refusal in its address (#3297).
    const [frame] = frames;
    if (frame === undefined) {
      throw new Error("no frame was appended");
    }
    expect(frame.isConnected).toBe(true);
    act(() => {
      sendBack(
        frame,
        `/tasks/${EXPORTED}/refused?refused_task=${EXPORTED}&refusal=409:STATE_FORBIDS_OPERATION:task_succeeded`,
      );
    });
    const card = exportCard();
    expect(await within(card).findByRole("alert")).toHaveTextContent(
      /^L’état actuel ne permet pas cette opération/,
    );
    // The frame the refusal came back in leaves the document at once, and its timer with it: five
    // minutes later, nothing is taken away twice (#3298).
    expect(frame.isConnected).toBe(false);
    await act(() => vi.advanceTimersByTimeAsync(FRAME_KEPT));
    expect(frames).toHaveLength(1);
    expect(vi.getTimerCount()).toBe(0);
    // Not served, the file is offered again: the click reads the task anew first.
    expect(within(card).getByRole("link", { name: /^Télécharger le résultat/ })).toBeVisible();
    expect(followed).toEqual([]);
    expect(window.location.pathname).toBe(EXCHANGES);
    expect(window.location.search).toBe("");
    expect(screen.getByRole("form", { name: "Demander un export" })).toBe(form);
    expect(kinds).toBeInTheDocument();
    expect(kinds.value).toBe(chosen);
  });

  it("tells the end of the session on its card when the frame comes to the sign-in page, which carries nothing of the refusal, the file offered again (#3297)", async () => {
    serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_succeeded",
    });
    render(shell(true));
    await ask();
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    await waitFor(() => {
      expect(frames).toHaveLength(1);
    });
    const [frame] = frames;
    if (frame === undefined) {
      throw new Error("no frame was appended");
    }
    act(() => {
      sendBack(frame, `/login?next=${encodeURIComponent(EXCHANGES)}`);
    });
    const card = exportCard();
    expect(await within(card).findByRole("alert")).toBeVisible();
    expect(frame.isConnected).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
    expect(within(card).getByRole("link", { name: /^Télécharger le résultat/ })).toBeVisible();
  });

  it("is not downloaded by itself once the screen that asked for it is left: its card offers it (#3103)", async () => {
    serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      [TASK]: "task_export_succeeded",
    });
    const view = render(shell(true));
    await ask();
    view.rerender(shell(false));
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL * 2));
    expect(frames).toEqual([]);
    expect(followed).toEqual([]);
    const cards = screen.getByRole("region", { name: "Aboutissements des tâches" });
    expect(within(cards).getByRole("link", { name: /^Télécharger le résultat/ })).toBeVisible();
  });

  it("is not downloaded when the read before it finds the result gone (#3103)", async () => {
    const client = serve({
      [EXPORT]: { example: "task_export_queued", status: 202 },
      // Read succeeded by the follow-up, then without its file — deleted after a first download.
      [TASK]: ["task_export_succeeded", "task_succeeded"],
    });
    render(shell(true));
    await ask();
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL * 2));
    expect(client.calls.filter((call) => call.route === TASK)).toHaveLength(2);
    expect(frames).toEqual([]);
    expect(followed).toEqual([]);
  });
});
