// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { BackgroundTask } from "@/api/problem";
import { STORAGE_KEY } from "@/components/tasks/storage";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { LAST_CONTEXT_COOKIE } from "@/navigation/context";
import { loadDocument } from "@/navigation/document";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { Shell } from "./shell";

// The server of Next, as far as signing out needs it: the fake back behind serverClient.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("@/navigation/document", () => ({ loadDocument: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => SCREEN,
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const SCREEN = `/projects/${PROJECT}/revisions`;
const SIGN_OUT = "DELETE /session";
const { user, permissions } = example("session") as components["schemas"]["Session"];

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A screen that has started a marking, which the tracker of the shell follows. */
function Marking() {
  const track = useTrackTask();
  return (
    <main>
      <button
        type="button"
        onClick={() => {
          track(example("task_mark_queued") as BackgroundTask, { subject: "V2" });
        }}
      >
        Marquer
      </button>
    </main>
  );
}

/** Render the shell of the account of the contract, on a screen of a project. */
function shell() {
  return render(
    <Shell
      locale="fr"
      account={user}
      preference="default"
      theme="default"
      permissions={permissions}
      remembered={SCREEN}
      sidebarOpen
    >
      <Marking />
    </Shell>,
  );
}

/** Sign out from the menu of the account. */
async function signOut() {
  await userEvent.click(screen.getByRole("button", { name: "Compte de Camille Martin" }));
  await userEvent.click(screen.getByRole("menuitem", { name: "Se déconnecter" }));
}

/** The last project context the browser keeps, as its cookie says it. */
function rememberedContext(): string | undefined {
  return document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith(`${LAST_CONTEXT_COOKIE}=`))
    ?.slice(LAST_CONTEXT_COOKIE.length + 1);
}

beforeEach(() => {
  vi.mocked(loadDocument).mockClear();
  window.sessionStorage.clear();
  document.cookie = `${LAST_CONTEXT_COOKIE}=${encodeURIComponent(SCREEN)}; path=/`;
});

describe("signing out from the menu of the account", () => {
  it("closes the session, forgets the last project and the tasks of the tab, and loads the sign-in page", async () => {
    const client = serve({ [SIGN_OUT]: { status: 204 }, "GET /tasks/{task_id}": "task_running" });
    shell();
    await userEvent.click(screen.getByRole("button", { name: "Marquer" }));
    expect(window.sessionStorage.getItem(STORAGE_KEY)).not.toBeNull();
    expect(rememberedContext()).toBe(encodeURIComponent(SCREEN));

    await signOut();

    expect(client.calls.map((call) => call.route)).toContain(SIGN_OUT);
    expect(rememberedContext()).toBeUndefined();
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(
      within(screen.getByRole("region", { name: "Tâches de fond" })).queryByRole("list"),
    ).toBeNull();
    expect(loadDocument).toHaveBeenCalledExactlyOnceWith("/login");
  });

  it("holds the user signed out when the session had already expired", async () => {
    serve({ [SIGN_OUT]: { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    shell();
    await signOut();
    expect(rememberedContext()).toBeUndefined();
    expect(loadDocument).toHaveBeenCalledExactlyOnceWith("/login");
  });

  it("says the API out of reach, and keeps what the session left, which still stands", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    shell();
    await signOut();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le service est injoignable ; réessayez dans un instant.",
    );
    expect(rememberedContext()).toBe(encodeURIComponent(SCREEN));
    expect(loadDocument).not.toHaveBeenCalled();
  });
});
