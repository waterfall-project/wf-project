// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApiClient } from "@/api/client";
import type { BackgroundTask } from "@/api/problem";
import type { ShellProps } from "@/components/shell/shell";
import { SIDEBAR_COOKIE } from "@/components/ui/sidebar-state";
import { LAST_CONTEXT_COOKIE } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, type FakeTiming, fakeClient } from "@/test/fixtures";

import RootLayout, { generateMetadata } from "./layout";

const server = vi.hoisted(() => ({
  client: undefined as FakeClient | undefined,
  acceptLanguage: "",
  cookie: undefined as string | undefined,
  sidebar: undefined as string | undefined,
  // What the cache of React holds for the request; a test is one request.
  cached: new Map<unknown, Map<string, unknown>>(),
  // The tasks of the user the layout handed the shell, for its tracker to follow.
  running: undefined as Promise<readonly BackgroundTask[]> | undefined,
}));

// The cache of React, as a server component sees it: a function it wraps runs once per
// request, however many components call it. Outside the renderer of the server, React's own
// runs it at every call, and the reads of a request could not be counted.
vi.mock("react", async (original) => {
  const react = await original<typeof import("react")>();
  const cache =
    <A extends unknown[], R>(fn: (...args: A) => R) =>
    (...args: A): R => {
      const calls = server.cached.get(fn) ?? new Map<string, unknown>();
      server.cached.set(fn, calls);
      const key = JSON.stringify(args);
      if (!calls.has(key)) {
        calls.set(key, fn(...args));
      }
      return calls.get(key) as R;
    };
  return { ...react, cache };
});

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// The shell itself, which keeps what the layout hands its tracker: the tracker follows it once
// mounted, which a document rendered on the server does not show.
vi.mock("@/components/shell/shell", async (original) => {
  const shell = await original<typeof import("@/components/shell/shell")>();
  return {
    ...shell,
    Shell: (props: ShellProps) => {
      server.running = props.running;
      return <shell.Shell {...props} />;
    },
  };
});
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": server.acceptLanguage })),
  cookies: () =>
    Promise.resolve({
      get: (name: string) => {
        const value = { [LAST_CONTEXT_COOKIE]: server.cookie, [SIDEBAR_COOKIE]: server.sidebar }[
          name
        ];
        return value === undefined ? undefined : { name, value };
      },
    }),
}));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
// The home page: the address the navigation reads, as the router of Next would give it.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const UNAUTHORIZED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;
const LAST =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102/risks";

/** A request from a browser asking for a language, by an account and its session. */
function request(acceptLanguage: string, answers: FakeAnswers = {}, timing: FakeTiming = {}) {
  server.client = fakeClient(
    {
      "GET /session": "session",
      "GET /installation": "installation",
      "GET /tasks": "tasks_none",
      ...answers,
    },
    timing,
  );
  server.acceptLanguage = acceptLanguage;
}

/** The document the layout renders around a page. */
async function page(): Promise<string> {
  return renderToStaticMarkup(await RootLayout({ children: <p>page</p> }));
}

beforeEach(() => {
  server.running = undefined;
  server.cookie = undefined;
  server.sidebar = undefined;
  server.cached.clear();
});

describe("RootLayout", () => {
  it("renders a page inside the shell, in English for a browser asking for English [WF-INTF-0160-A]", async () => {
    request("en-US,en;q=0.9");
    const html = await page();
    expect(html).toMatch(/^<html lang="en" class="font-geist-sans"><head><\/head><body>/);
    expect(html).toContain('aria-label="Functions"');
    expect(html).toContain('aria-label="Account of Camille Martin"');
    expect(html).toContain('placeholder="Search for a function, a project…"');
    expect(html).toContain("<p>page</p>");
  });

  it("renders in French for a browser asking for French [WF-INTF-0160-A]", async () => {
    request("fr-FR,fr;q=0.9");
    const html = await page();
    expect(html).toMatch(/^<html lang="fr"/);
    expect(html).toContain('aria-label="Fonctions"');
    expect(html).toContain('aria-label="Compte de Camille Martin"');
  });

  it("lets the workstation decide the mode of an account that follows it", async () => {
    request("fr");
    const html = await page();
    expect(html).not.toContain("data-theme");
    expect(html).toContain(
      '<source srcSet="/waterfall_logo-dark.svg" media="(prefers-color-scheme: dark)"/>',
    );
  });

  it("forces the mode the account chose on the whole document", async () => {
    request("fr", { "GET /session": "session_dark" });
    const html = await page();
    expect(html).toMatch(/^<html lang="fr" data-theme="dark"/);
    expect(html).toContain('<source srcSet="/waterfall_logo-dark.svg" media="all"/>');
  });

  it("offers the functions of the session, and leads back to the project the cookie kept", async () => {
    request("fr");
    server.cookie = `${LAST}?as_of=2026-05-31`;
    const html = await page();
    expect(html).toContain('<nav aria-label="Fonctions"');
    // No page of a block of the FBS is shown: each is closed on its functions.
    expect(html).toMatch(/<button[^>]*aria-expanded="false"[^>]*>.*?<span>Portefeuille<\/span>/);
    expect(html).toMatch(/<a[^>]*href="\/"[^>]*><svg[^>]*>.*?<\/svg><span>Projets<\/span>/);
    expect(html).toMatch(
      new RegExp(`<a[^>]*href="${LAST}\\?as_of=2026-05-31"[^>]*><svg[^>]*aria-hidden="true"`),
    );
    expect(html).toContain("Retour au projet</span></a>");
  });

  it("leads nowhere from a cookie that names no project", async () => {
    request("fr");
    server.cookie = "https://elsewhere.example/";
    expect(await page()).not.toContain("Retour au projet");
  });

  it("renders the side bar as the user left it: unfolded, unless folded", async () => {
    request("fr");
    expect(await page()).toContain('data-state="expanded"');
    server.sidebar = "false";
    server.cached.clear();
    expect(await page()).toContain('data-state="collapsed"');
  });

  it("offers neither the menu of the account nor functions without a session: the browser decides", async () => {
    request("en", { "GET /session": UNAUTHORIZED });
    const html = await page();
    expect(html).toMatch(/^<html lang="en" class="font-geist-sans">/);
    expect(html).not.toContain("Account of");
    expect(html).not.toContain('aria-label="Functions"');
    expect(html).toContain('alt="Waterfall"');
    expect(html).toContain("<p>page</p>");
  });

  it("still offers the status screen when the session cannot be read: the API is out of reach", async () => {
    server.client = Object.assign(
      createApiClient({
        address: "http://unreachable.invalid",
        fetch: () => Promise.reject(new TypeError("fetch failed")),
      }),
      { calls: [] },
    );
    server.acceptLanguage = "fr";
    const html = await page();
    expect(html).not.toContain("Compte de");
    expect(html).toContain('<nav aria-label="Fonctions"');
    expect([...html.matchAll(/<a [^>]*href="([^"]*)"/g)].map((match) => match[1])).toEqual([
      "/",
      "/system",
    ]);
    expect(html).toContain("<p>page</p>");
    // No session to ask the tasks of: none is asked.
    expect(server.running).toBeUndefined();
  });

  it("reads the session once, and the account through it alone", async () => {
    request("de-DE");
    await page();
    await server.running;
    const routes = server.client?.calls.map((call) => call.route);
    // The browser asks for no language offered: the installation decides. The tasks of the
    // user that still run are asked once the session is known to be open, for the tracker.
    expect(routes).toEqual(["GET /session", "GET /installation", "GET /tasks"]);
    const tasks = server.client?.calls.find((call) => call.route === "GET /tasks");
    expect(tasks?.query.get("status")).toBe("queued,running");
  });

  it("hands the tracker of the shell the tasks of the user that still run", async () => {
    request("fr", { "GET /tasks": "tasks_running" });
    expect(await page()).toContain("<p>page</p>");
    const tasks = await server.running;
    expect(tasks?.map((task) => [task.task_id, task.status])).toEqual([
      ["01926f3a-7c00-7000-8000-000000000901", "running"],
    ]);
  });

  it("renders the document without waiting for the tasks of the user", async () => {
    // The list never answers: the document is rendered all the same, the promise still pending.
    request(
      "fr",
      {},
      { hold: (route) => (route === "GET /tasks" ? new Promise(() => undefined) : undefined) },
    );
    const html = await page();
    expect(html).toContain('aria-label="Compte de Camille Martin"');
    expect(html).toContain("<p>page</p>");
    expect(server.client?.calls.map((call) => call.route)).toContain("GET /tasks");
    const settled = await Promise.race([
      server.running?.then(() => "answered"),
      new Promise((resolve) => setTimeout(resolve, 50, "pending")),
    ]);
    expect(settled).toBe("pending");
  });

  it("asks no task without a session, and hands the tracker none when the API refuses the list", async () => {
    request("fr", { "GET /session": UNAUTHORIZED, "GET /tasks": "tasks_running" });
    expect(await page()).toContain("<p>page</p>");
    expect(server.running).toBeUndefined();
    expect(server.client?.calls.map((call) => call.route)).not.toContain("GET /tasks");
    server.cached.clear();
    request("fr", { "GET /tasks": UNAUTHORIZED });
    const html = await page();
    expect(html).toContain('aria-label="Compte de Camille Martin"');
    expect(await server.running).toEqual([]);
  });

  it("asks the installation once for a request whose browser leaves it the language", async () => {
    request("*");
    await page();
    await generateMetadata();
    const routes = server.client?.calls.map((call) => call.route);
    expect(routes).toEqual(["GET /session", "GET /installation", "GET /tasks"]);
  });

  it("titles the document with the product, from the catalogue", async () => {
    request("en");
    expect((await generateMetadata()).title).toBe("Waterfall");
  });
});
