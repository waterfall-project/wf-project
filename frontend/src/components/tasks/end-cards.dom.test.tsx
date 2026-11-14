// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { closeTasks, tasksButton, tasksRegion } from "@/test/task-panel";

import { EndCards } from "./end-cards";
import { POLL_INTERVAL } from "./task-entry";
import { TaskPanel, TasksButton, TaskTracker, useTrackTask } from "./task-tracker";

// The cards of the ends of the tasks, in the corner of the window (US-2170, decided by the author on
// 2026-11-14); the rest of the tracker is in `task-tracker.dom.test.tsx`. The server of Next, as far
// as the tracker needs it, and its router.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => window.location.pathname,
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISIONS = `/projects/${PROJECT}/revisions`;
const ELSEWHERE = `/projects/${PROJECT}/exchanges`;
const EXPORTED = "01926f3a-7c00-7000-8000-000000000935";
const TASK = "GET /tasks/{task_id}";
const SHOWN = window.location.href;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A screen that hands the task of the contract named over to the tracker, by its button. */
function Starting({ names }: { readonly names: readonly string[] }) {
  const track = useTrackTask();
  return (
    <>
      {names.map((name) => (
        <button
          key={name}
          type="button"
          onClick={() => {
            track(example(name) as BackgroundTask);
          }}
        >
          {`Lancer ${name}`}
        </button>
      ))}
      <button type="button">Ailleurs</button>
    </>
  );
}

/** Render the shell, as far as the cards go: the tracker, its button, its panel, and the cards. */
function shell(...names: string[]) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker>
        <header>
          <TasksButton />
        </header>
        <TaskPanel />
        <main>
          <Starting names={names} />
        </main>
        <EndCards />
      </TaskTracker>
    </NextIntlClientProvider>,
  );
}

/** Hand a task over from the screen of the revisions. */
async function start(name: string) {
  await userEvent.click(screen.getByRole("button", { name: `Lancer ${name}` }));
}

/** Let the time of one read go by, and the read be answered. */
async function tick(times = 1) {
  for (let turn = 0; turn < times; turn += 1) {
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
  }
}

/** The stack of the cards. */
function stack() {
  return screen.getByRole("region", { name: "Aboutissements des tâches" });
}

/** The cards of the stack, by the sentence each says, from the top. */
function cards() {
  return within(stack())
    .getAllByRole("group")
    .map((card) => card.getAttribute("aria-labelledby"))
    .map((id) => document.getElementById(id ?? "")?.textContent);
}

/** Whether each click on a link went on to the browser, recorded — and stopped there. */
let followed: string[] = [];

/** Record the link a click went on to, and stop it there: happy-dom follows no link. */
function record(event: Event) {
  const link = event.target instanceof Element ? event.target.closest("a") : null;
  if (link !== null) {
    if (!event.defaultPrevented) {
      followed.push(link.getAttribute("href") ?? "");
    }
    event.preventDefault();
  }
}

beforeEach(() => {
  followed = [];
  vi.useFakeTimers({ shouldAdvanceTime: true });
  window.sessionStorage.clear();
  window.history.replaceState(null, "", REVISIONS);
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

describe("the card of the end of a task", () => {
  it("tells a user gone to another screen the end of the treatment, by a card that stays, announced without taking the focus and noted in the history [WF-IHM-0080-A]", async () => {
    // Un utilisateur qui change d'écran pendant un import est informé de son aboutissement.
    serve({ [TASK]: ["task_running", "task_succeeded"] });
    shell("task_mark_queued");
    await start("task_mark_queued");
    window.history.replaceState(null, "", ELSEWHERE);
    screen.getByRole("button", { name: "Ailleurs" }).focus();
    await tick();
    expect(screen.queryByRole("region", { name: "Aboutissements des tâches" })).toBeNull();
    await tick();
    const sentence = "Tâche terminée\u00A0: Marquage d’une révision.";
    expect(cards()).toEqual([sentence]);
    // Announced by the log of the ends, the focus left where it was.
    expect(screen.getByRole("log").textContent).toBe(sentence);
    expect(screen.getByRole("button", { name: "Ailleurs" })).toHaveFocus();
    // It stays: no time takes it away.
    await tick(5);
    expect(cards()).toEqual([sentence]);
    // The panel keeps it, in the history of the messages.
    const panel = tasksRegion().closest("[role=dialog]");
    expect(panel).not.toBeNull();
    expect(
      within(panel as HTMLElement).getByRole("region", { name: "Messages" }),
    ).toHaveTextContent(/Tâche terminée\s: Marquage d’une révision\./);
    closeTasks();
  });

  it("opens the screen a revision was marked from, and goes once opened [WF-IHM-0080-A]", async () => {
    serve({ [TASK]: "task_succeeded" });
    shell("task_mark_queued");
    await start("task_mark_queued");
    window.history.replaceState(null, "", ELSEWHERE);
    await tick();
    const open = within(stack()).getByRole("link", {
      name: /^Ouvrir\s: Marquage d’une révision — /,
    });
    expect(open).toHaveTextContent("Ouvrir");
    expect(open).toHaveAttribute("href", REVISIONS);
    fireEvent.click(open);
    expect(screen.queryByRole("region", { name: "Aboutissements des tâches" })).toBeNull();
  });

  it("stays when « Ouvrir » opens another tab or window, a modified click [WF-IHM-0080-A]", async () => {
    serve({ [TASK]: "task_succeeded" });
    shell("task_mark_queued");
    await start("task_mark_queued");
    await tick();
    const open = within(stack()).getByRole("link", { name: /^Ouvrir\s: / });
    fireEvent.click(open, { ctrlKey: true });
    fireEvent.click(open, { metaKey: true });
    fireEvent.click(open, { shiftKey: true });
    fireEvent.click(open, { button: 1 });
    expect(cards()).toEqual(["Tâche terminée\u00A0: Marquage d’une révision."]);
  });

  it("says the motive of a failure, and opens the screen where the treatment runs again [WF-IHM-0080-A]", async () => {
    // L'échec d'un traitement de fond est signalé avec son motif, et le même traitement peut être
    // relancé : from the screen it was started from.
    serve({ [TASK]: "task_failed" });
    shell("task_mark_queued");
    await start("task_mark_queued");
    await tick();
    const card = within(stack()).getByRole("group");
    expect(card).toHaveTextContent(/^Tâche échouée\s: Marquage d’une révision\./);
    expect(card).toHaveTextContent(/Ingénierie électrique/);
    expect(within(card).getByRole("link", { name: /^Ouvrir\s: / })).toHaveAttribute(
      "href",
      REVISIONS,
    );
  });

  it("downloads the file of an export, read anew first, and goes once the download has left [WF-IHM-0080-A]", async () => {
    const client = serve({ [TASK]: "task_export_succeeded" });
    shell("task_export_succeeded");
    await start("task_export_succeeded");
    const download = within(stack()).getByRole("link", {
      name: /^Télécharger le résultat\s: Export$/,
    });
    expect(download).toHaveTextContent("Télécharger");
    await userEvent.click(download);
    await waitFor(() => {
      expect(followed).toEqual([`/tasks/${EXPORTED}/result?from=${encodeURIComponent(REVISIONS)}`]);
    });
    expect(client.calls.map((call) => call.path)).toEqual([`/tasks/${EXPORTED}`]);
    expect(screen.queryByRole("region", { name: "Aboutissements des tâches" })).toBeNull();
  });

  it("stays and says why when the result is refused, downloading nothing [WF-IHM-0080-A]", async () => {
    serve({ [TASK]: { problem: { code: "NOT_FOUND", status: 404 } } });
    shell("task_export_succeeded");
    await start("task_export_succeeded");
    await userEvent.click(within(stack()).getByRole("link", { name: /^Télécharger/ }));
    expect(await within(stack()).findByRole("alert")).toHaveTextContent(/^Introuvable/);
    expect(followed).toEqual([]);
  });

  it("gives the focus on to the next card once the download has left from the keyboard, the card gone [WF-IHM-0080-A]", async () => {
    // The read of the marking, then the read before the download.
    serve({ [TASK]: ["task_succeeded", "task_export_succeeded"] });
    shell("task_mark_queued", "task_export_succeeded");
    await start("task_mark_queued");
    await tick();
    await start("task_export_succeeded");
    within(stack())
      .getByRole("link", { name: /^Télécharger le résultat/ })
      .focus();
    await userEvent.keyboard("{Enter}");
    await waitFor(() => {
      expect(followed).toHaveLength(1);
    });
    expect(cards()).toEqual(["Tâche terminée\u00A0: Marquage d’une révision."]);
    expect(
      within(stack()).getByRole("button", { name: /^Fermer la carte\s: Marquage d’une révision$/ }),
    ).toHaveFocus();
  });

  it("offers the file no more once read anew and found gone, saying so, the focus on its cross [WF-IHM-0080-A]", async () => {
    // Read without its file: served once, downloaded already (WF-DAT-0120) — the contract has no
    // export without its file, the fake back answers a task succeeded without one, a marking.
    serve({ [TASK]: "task_succeeded" });
    shell("task_export_succeeded");
    await start("task_export_succeeded");
    const card = within(stack()).getByRole("group", { name: /^Tâche terminée\s: Export\.$/ });
    within(card)
      .getByRole("link", { name: /^Télécharger le résultat/ })
      .focus();
    await userEvent.keyboard("{Enter}");
    expect(await within(card).findByRole("alert")).toHaveTextContent(
      "Le résultat de cette tâche n’est plus disponible.",
    );
    expect(within(card).queryByRole("link", { name: /^Télécharger/ })).toBeNull();
    expect(within(card).getByRole("button", { name: /^Fermer la carte\s: Export$/ })).toHaveFocus();
    expect(followed).toEqual([]);
  });

  it("stacks the ends, the last on top, and gives the focus on from one closed cross to the next, then to the button of the bar [WF-IHM-0080-A]", async () => {
    serve({ [TASK]: "task_succeeded" });
    shell("task_mark_queued", "task_export_succeeded");
    await start("task_mark_queued");
    await tick();
    await start("task_export_succeeded");
    expect(cards()).toEqual([
      "Tâche terminée\u00A0: Export.",
      "Tâche terminée\u00A0: Marquage d’une révision.",
    ]);
    await expectAccessible(stack());
    within(stack())
      .getByRole("button", { name: /^Fermer la carte\s: Export$/ })
      .focus();
    await userEvent.keyboard("{Enter}");
    expect(cards()).toEqual(["Tâche terminée\u00A0: Marquage d’une révision."]);
    expect(
      within(stack()).getByRole("button", { name: /^Fermer la carte\s: Marquage d’une révision$/ }),
    ).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(screen.queryByRole("region", { name: "Aboutissements des tâches" })).toBeNull();
    expect(tasksButton()).toHaveFocus();
    // Closed, the tasks are still followed, and the panel still lists them.
    expect(tasksButton()).toHaveAccessibleName(/^Tâches et messages\s: 2 tâches suivies/);
  });

  it("has none for a follow-up interrupted, which says nothing of the task [WF-IHM-0080-A]", async () => {
    serve({ [TASK]: { problem: { code: "NOT_FOUND", status: 404 } } });
    shell("task_mark_queued");
    await start("task_mark_queued");
    await tick();
    expect(screen.getByRole("log")).toHaveTextContent(/^Suivi interrompu/);
    expect(screen.queryByRole("region", { name: "Aboutissements des tâches" })).toBeNull();
  });
});
