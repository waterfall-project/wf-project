// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { TaskPanel, TaskTracker, useTrackTask } from "./task-tracker";

// The server of Next, as far as the tracker needs it: the fake back behind serverClient, and the
// screen shown.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const SCREEN = "/projects/01926f3a-7c00-7000-8000-000000000001/revisions";

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: vi.fn() }),
  usePathname: () => SCREEN,
  useSearchParams: () => new URLSearchParams("subproject_id=unassigned"),
}));

const EXPORTED = "01926f3a-7c00-7000-8000-000000000935";
const TASK = "GET /tasks/{task_id}";
/** Where the result of the export is downloaded from, leaving from the screen shown. */
const RESULT_HREF = `/tasks/${EXPORTED}/result?from=${encodeURIComponent(`${SCREEN}?subproject_id=unassigned`)}`;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The export the screen hands over to the tracker, once the API answered its request. */
function Exporting() {
  const track = useTrackTask();
  return (
    <button
      type="button"
      onClick={() => {
        track(example("task_export_succeeded") as BackgroundTask);
      }}
    >
      Exporter
    </button>
  );
}

/** Render the tracker and its panel. */
function tracker() {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker signedIn={false}>
        <TaskPanel />
        <Exporting />
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

/** Render the tracker, and hand it the export. */
async function exported() {
  tracker();
  await userEvent.click(screen.getByRole("button", { name: "Exporter" }));
}

/** The offer to download the result of the export. */
function downloadLink() {
  return screen.getByRole("link", { name: /^Télécharger le résultat/ });
}

/**
 * The browser following a link: the click the entry lets through replayed as the browser would, an
 * event its handler may prevent; whether each click went on to the browser, recorded — and stopped
 * there, happy-dom following no link.
 */
let followed: boolean[] = [];

beforeEach(() => {
  followed = [];
  window.sessionStorage.clear();
  window.history.replaceState(null, "", SCREEN);
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
});

/** Record whether a click on a link went on to the browser, and stop it there. */
function record(event: Event) {
  if (event.target instanceof Element && event.target.closest("a") !== null) {
    followed.push(!event.defaultPrevented);
    event.preventDefault();
  }
}

describe("the result of a task", () => {
  it("is downloaded once the server says it is still there, from the screen shown, each download read anew, and a refusal of the read is told in place", async () => {
    const client = serve({
      [TASK]: [{ problem: { code: "NOT_FOUND", status: 404 } }, "task_export_succeeded"],
    });
    await exported();
    const link = downloadLink();
    // No `download`: a refusal of the route brings the browser back to the screen.
    expect(link).toHaveAttribute("href", RESULT_HREF);
    expect(link).not.toHaveAttribute("download");
    // The task gone: the refusal is told by the notice of the entry, the follow-up not interrupted.
    await userEvent.click(link);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Introuvable : cet élément n’existe pas, ou vous n’y avez pas accès.",
    );
    expect(screen.queryByText("Suivi interrompu")).not.toBeInTheDocument();
    expect(followed).toEqual([false]);
    // The result there: the click replayed goes on to the browser, and the notice goes.
    await userEvent.click(link);
    await vi.waitFor(() => {
      expect(followed).toEqual([false, false, true]);
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(client.calls.map((call) => call.path)).toEqual([
      `/tasks/${EXPORTED}`,
      `/tasks/${EXPORTED}`,
    ]);
  });

  it("says the result no longer available when the task read anew gives none, and offers no download", async () => {
    // A task read without a result: the example of the contract is a marking, which made none.
    serve({ [TASK]: "task_succeeded" });
    await exported();
    await userEvent.click(downloadLink());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le résultat de cette tâche n’est plus disponible.",
    );
    expect(
      screen.queryByRole("link", { name: /^Télécharger le résultat/ }),
    ).not.toBeInTheDocument();
    expect(followed).toEqual([false]);
  });

  it("downloads nothing when the entry is dismissed while the task is read anew", async () => {
    let release!: () => void;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.client = fakeClient(
      { [TASK]: "task_export_succeeded" },
      { hold: (route) => (route === TASK ? held : undefined) },
    );
    await exported();
    await userEvent.click(downloadLink());
    await userEvent.click(screen.getByRole("button", { name: /^Retirer du suivi/ }));
    release();
    await act(() => held);
    await act(() => Promise.resolve());
    // No click replayed: the entry gone, the download does not leave.
    expect(followed).toEqual([false]);
  });
});

describe("the refusal of a result the browser came back with", () => {
  /** The address the browser shows. */
  const shown = () => `${window.location.pathname}${window.location.search}`;

  beforeEach(() => {
    // The time of the tracker is the test's: the address is cleaned when the test lets it.
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("is told by the entry of the task, read and followed again, and leaves the address once the page is revealed (#416)", async () => {
    // The route sent the browser back: the result expired between the read and the download.
    const refused = `${SCREEN}?subproject_id=unassigned&refused_task=${EXPORTED}&refusal=409:STATE_FORBIDS_OPERATION`;
    window.history.replaceState(null, "", refused);
    const client = serve({ [TASK]: "task_export_succeeded" });
    tracker();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération.",
    );
    expect(screen.getByText("Export")).toBeInTheDocument();
    expect(downloadLink()).toBeInTheDocument();
    expect(client.calls.map((call) => call.path)).toEqual([`/tasks/${EXPORTED}`]);
    // Not while the page the document streamed may still be pending: a while after it loaded.
    expect(shown()).toBe(refused);
    await act(() => vi.advanceTimersByTimeAsync(1_000));
    expect(shown()).toBe(`${SCREEN}?subproject_id=unassigned`);
  });

  it("says the API out of reach, and an unknown code as the unexpected error", async () => {
    serve({ [TASK]: "task_export_succeeded" });
    window.history.replaceState(null, "", `${SCREEN}?refused_task=${EXPORTED}&refusal=unreachable`);
    const first = tracker();
    expect(await screen.findByRole("alert")).toHaveTextContent(/Le service est injoignable/);
    first.unmount();
    window.history.replaceState(null, "", `${SCREEN}?refused_task=${EXPORTED}&refusal=502:NOPE`);
    tracker();
    expect(await screen.findByRole("alert")).toHaveTextContent("Erreur inattendue du service.");
  });

  it("is told by the panel itself when the task cannot be read again, until the user closes it", async () => {
    const client = serve({ [TASK]: { problem: { code: "NOT_FOUND", status: 404 } } });
    window.history.replaceState(
      null,
      "",
      `${SCREEN}?refused_task=${EXPORTED}&refusal=409:STATE_FORBIDS_OPERATION`,
    );
    tracker();
    const panel = screen.getByRole("region", { name: "Tâches de fond" });
    expect(await within(panel).findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération.",
    );
    expect(panel).toHaveTextContent("Le résultat d’une tâche n’a pas pu être téléchargé.");
    expect(within(panel).queryByRole("listitem")).not.toBeInTheDocument();
    expect(client.calls).toHaveLength(1);
    await userEvent.click(within(panel).getByRole("button", { name: "Fermer l’avis" }));
    expect(panel).not.toHaveTextContent("Le résultat d’une tâche n’a pas pu être téléchargé.");
  });

  it("asks nothing for an address that carries no refusal it can stand for", async () => {
    const client = serve({});
    window.history.replaceState(null, "", `${SCREEN}?refused_task=${EXPORTED}&refusal=conflict`);
    tracker();
    await act(() => vi.advanceTimersByTimeAsync(1_000));
    expect(client.calls).toEqual([]);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(shown()).toBe(`${SCREEN}?refused_task=${EXPORTED}&refusal=conflict`);
  });
});
