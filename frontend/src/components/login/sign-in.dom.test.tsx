// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import { PasswordForm } from "@/components/account/password-form";
import { POLL_INTERVAL } from "@/components/tasks/task-entry";
import { TaskPanel, TaskTracker, useTrackTask } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { loadDocument } from "@/navigation/document";
import { NEXT_PARAMETER, returnTarget } from "@/navigation/login";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { SignInForm } from "./sign-in-form";

// The server of Next, as far as the forms need it: the fake back behind serverClient.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
// The address the browser shows, which the way to the sign-in page comes back to.
const address = vi.hoisted(() => ({ pathname: "/", search: new URLSearchParams() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: () => undefined }));
vi.mock("@/navigation/document", () => ({ loadDocument: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: () => undefined }),
  usePathname: () => address.pathname,
  useSearchParams: () => address.search,
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const MARKING = "01926f3a-7c00-7000-8000-000000000901";
const EXPIRED = { problem: { code: "SESSION_EXPIRED", status: 401 } } as const;
// The session of the contract, which the fake back opens: the named example of openSession.
const OPENED = { example: "session", status: 201 } as const;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A page in French, as the shell hands it its texts. */
function inFrench(page: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {page}
    </NextIntlClientProvider>
  );
}

/** Type credentials in the form, and submit them. */
async function signInWith(email: string, password: string) {
  await userEvent.type(screen.getByLabelText("Adresse électronique"), email);
  await userEvent.type(screen.getByLabelText("Mot de passe"), password);
  await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
}

/** Show an address, as a navigation of the browser would. */
function visit(pathname: string, search = "") {
  address.pathname = pathname;
  address.search = new URLSearchParams(search);
}

/** Where the link to the sign-in page leads back to, once signed in. */
function nextOf(link: HTMLElement): string {
  const href = new URL(link.getAttribute("href") ?? "", "http://front.invalid");
  expect(href.pathname).toBe("/login");
  return returnTarget(href.searchParams.get(NEXT_PARAMETER));
}

beforeEach(() => {
  vi.mocked(loadDocument).mockClear();
  window.sessionStorage.clear();
  visit("/");
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the form of the sign-in page", () => {
  it("opens the session with what was typed, and loads the screen the user was headed for", async () => {
    const client = serve({ "POST /session": OPENED });
    const { container } = render(inFrench(<SignInForm target="/projects" />));
    await expectAccessible(container);

    await signInWith("camille.martin@example.com", "court");

    // No rule of the password in the front: what was typed goes to the API, which judges it.
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      ["POST /session", { email: "camille.martin@example.com", password: "court" }],
    ]);
    expect(loadDocument).toHaveBeenCalledExactlyOnceWith("/projects");
  });

  it("tells credentials the API refuses by the code of the catalogue, and stays", async () => {
    serve({ "POST /session": { problem: { code: "INVALID_CREDENTIALS", status: 401 } } });
    render(inFrench(<SignInForm target="/" />));

    await signInWith("camille.martin@example.com", "pas le bon mot de passe");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Adresse électronique ou mot de passe incorrect.");
    // A refusal of the credentials, not a session to open: no way to the page it is on.
    expect(within(alert).queryByRole("link")).toBeNull();
    expect(loadDocument).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Se connecter" })).toBeEnabled();
  });

  it("gives every field its name, and its button its icon", () => {
    render(inFrench(<SignInForm target="/" />));
    expect(screen.getByLabelText("Adresse électronique")).toHaveAttribute(
      "autocomplete",
      "username",
    );
    expect(screen.getByLabelText("Mot de passe")).toHaveAttribute(
      "autocomplete",
      "current-password",
    );
    expect(
      screen.getByRole("button", { name: "Se connecter" }).querySelector("svg"),
    ).toHaveAttribute("aria-hidden", "true");
  });
});

describe("a session that expires on the way", () => {
  it("leads to the sign-in page, which, signed in again, leads back to the screen aimed at", async () => {
    // The user changes the password; the session has expired meanwhile.
    visit("/account/password");
    const client = serve({ "PUT /me/password": EXPIRED, "POST /session": OPENED });
    const view = render(inFrench(<PasswordForm />));
    await userEvent.type(screen.getByLabelText("Mot de passe actuel"), "ancien mot de passe");
    await userEvent.type(screen.getByLabelText("Nouveau mot de passe"), "nouveau mot de passe");
    await userEvent.click(screen.getByRole("button", { name: "Changer le mot de passe" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Votre session a expiré ; reconnectez-vous.");
    const target = nextOf(within(alert).getByRole("link", { name: "Se connecter" }));
    expect(target).toBe("/account/password");

    // The sign-in page, which the link leads to, and the session opened again.
    view.unmount();
    visit("/login", `${NEXT_PARAMETER}=${encodeURIComponent(target)}`);
    render(inFrench(<SignInForm target={target} />));
    await signInWith("camille.martin@example.com", "mot de passe de Camille");

    expect(client.calls.map((call) => call.route)).toEqual(["PUT /me/password", "POST /session"]);
    expect(loadDocument).toHaveBeenCalledExactlyOnceWith("/account/password");
  });

  it("follows on, once signed in again, the background tasks the lost session interrupted", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const tick = () => act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL));
    const screenAt = `/projects/${PROJECT}/revisions`;
    visit(screenAt, `revision_id=${REVISION}`);
    serve({ "GET /tasks/{task_id}": EXPIRED, "POST /session": OPENED });

    /** A screen that has started a marking, and the tracker of the shell that follows it. */
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
    const shell = (page: ReactNode) =>
      inFrench(
        <TaskTracker>
          <TaskPanel />
          {page}
        </TaskTracker>,
      );
    const view = render(shell(<Marking />));
    await userEvent.click(screen.getByRole("button", { name: "Marquer" }));
    await tick();

    // The read of the task found the session gone: its follow-up is interrupted, and leads to
    // the sign-in page.
    const panel = screen.getByRole("region", { name: "Tâches de fond" });
    expect(within(panel).getByText("Suivi interrompu")).toBeVisible();
    const target = nextOf(within(panel).getByRole("link", { name: "Se connecter" }));
    expect(target).toBe(`${screenAt}?revision_id=${REVISION}`);

    view.unmount();
    render(inFrench(<SignInForm target={target} />));
    await signInWith("camille.martin@example.com", "mot de passe de Camille");
    expect(loadDocument).toHaveBeenCalledExactlyOnceWith(target);

    // The document loaded anew: the tracker finds the task the tab kept, and follows it on.
    const reads = serve({ "GET /tasks/{task_id}": "task_succeeded" });
    render(shell(<main />));
    await tick();
    expect(reads.calls.map((call) => call.path)).toEqual([`/tasks/${MARKING}`]);
    expect(
      within(screen.getByRole("log")).getByText("Tâche terminée : Marquage d’une révision « V2 »."),
    ).toBeInTheDocument();
  });
});
