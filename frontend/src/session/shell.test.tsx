// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(home)/page";
import SignInUnavailablePage from "@/app/login/unavailable/page";
import SystemStatusPage from "@/app/system/page";
import { SESSION_LOST_DIGEST, SESSION_REQUIRED_DIGEST } from "@/components/system/failure";
import { SystemFailure } from "@/components/system/system-failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { requestConfig } from "@/i18n/request";
import { cookieJar } from "@/test/session";

import { requestSessionState } from "./request";
import { SIGN_IN_REFUSED_COOKIE } from "./tokens";

// A browser that holds no cookie at all, and sends no Accept-Language: nothing mocked of the
// session, of the client of the API or of the reads of the shell. Only the network is stubbed.
const browser = vi.hoisted((): { cookies: Record<string, string> } => ({ cookies: {} }));
vi.mock("next/headers", () => ({
  cookies: () => Promise.resolve(cookieJar(browser.cookies)),
  headers: () => Promise.resolve(new Headers()),
}));

/** Stub the network: the paths it is asked for, answered by the API of a platform. */
function stubNetwork(answer: (path: string) => Response): string[] {
  const reached: string[] = [];
  vi.stubGlobal("fetch", (request: Request) => {
    const { pathname } = new URL(request.url);
    reached.push(pathname);
    return Promise.resolve(answer(pathname));
  });
  return reached;
}

// The address the browser shows, as the router of Next gives it to a client component.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => {
  browser.cookies = {};
  vi.unstubAllGlobals();
});

describe("the reads of the shell without any cookie (#2914, #687)", () => {
  it("leave without a token and are never the session lost: the account of the layout is a 401, so the page of a platform out of reach is shown, not led to the sign-in page again [WF-SEC-0020-A]", async () => {
    const reached = stubNetwork(() =>
      Response.json({ code: "SESSION_REQUIRED", status: 401 }, { status: 401 }),
    );
    const state = await requestSessionState();
    expect(state).toEqual({ kind: "signed_out" });
    expect(reached).toHaveLength(1);
  });

  it("decide the language from the installation, without the session lost [WF-SEC-0020-A]", async () => {
    const reached = stubNetwork(() => Response.json({ default_language: "en" }));
    const { locale } = await requestConfig();
    expect(locale).toBe("en");
    expect(reached.some((path) => path.endsWith("/installation"))).toBe(true);
  });

  it("are only those of the shell: `serverClient()` strict, without a cookie, does not leave [WF-SEC-0020-A]", async () => {
    const { serverClient } = await import("@/api/server");
    const reached = stubNetwork(() => Response.json({}));
    await expect(serverClient().GET("/system/status")).rejects.toMatchObject({
      digest: SESSION_LOST_DIGEST,
    });
    expect(reached).toEqual([]);
  });

  it("let the page of a service out of reach render, the account unreadable, never led to the sign-in page again [WF-SEC-0020-A] (#2914)", async () => {
    const reached: string[] = [];
    vi.stubGlobal("fetch", (request: Request) => {
      reached.push(new URL(request.url).pathname);
      return Promise.reject(new TypeError("fetch failed"));
    });
    expect(await requestSessionState()).toEqual({ kind: "unreadable" });
    const { locale, messages } = await requestConfig();
    const page = await SignInUnavailablePage({ searchParams: Promise.resolve({ next: "/" }) });
    const html = renderToStaticMarkup(
      <NextIntlClientProvider locale={locale} messages={messages}>
        {page}
      </NextIntlClientProvider>,
    );
    expect(html).toContain('href="/login?next=%2F"');
    expect(reached.length).toBeGreaterThan(0);
  });

  it("lead the screen of the system status, which needs a session, to the sign-in page before any call [WF-SEC-0020-A] (#2914)", async () => {
    const reached = stubNetwork(() => Response.json({}));
    await expect(SystemStatusPage()).rejects.toMatchObject({ digest: SESSION_LOST_DIGEST });
    expect(reached).toEqual([]);
  });
});

describe("the home after a sign-in the realm refused (#2914)", () => {
  it("is refused by the API for want of a session, said « Session requise » with its link, and neither lost nor led to the sign-in page by itself [WF-SEC-0020-A]", async () => {
    browser.cookies = { [SIGN_IN_REFUSED_COOKIE]: "1" };
    const reached = stubNetwork(() =>
      Response.json({ code: "SESSION_REQUIRED", status: 401 }, { status: 401 }),
    );
    const refused = await HomePage({ searchParams: Promise.resolve({}) }).then(
      () => undefined,
      (error: unknown) => error as Error & { digest?: string },
    );
    // The API was asked, without a token: the request left, and its 401 is what the screen says.
    expect(reached.length).toBeGreaterThan(0);
    expect(refused?.digest).toBe(SESSION_REQUIRED_DIGEST);
    expect(refused?.digest).not.toBe(SESSION_LOST_DIGEST);
    const html = renderToStaticMarkup(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <SystemFailure error={refused as Error & { digest: string }} retry={vi.fn()} />
      </NextIntlClientProvider>,
    );
    expect(html).toContain("Session requise");
    expect(html).toContain('href="/login?next=%2F"');
  });
});
