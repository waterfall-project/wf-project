// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { CATALOGUES } from "./catalogues";
import { requestConfig, requestLanguage } from "./request";

// The session and its account come from the fake back, the Accept-Language header from the request.
const server = vi.hoisted(() => ({
  client: undefined as ApiClient | undefined,
  acceptLanguage: null as string | null,
}));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/headers", () => ({
  headers: () => {
    const header = server.acceptLanguage;
    return Promise.resolve(new Headers(header === null ? {} : { "accept-language": header }));
  },
}));

const INSTALLATION = "GET /installation";

/** Serve the account and the installation, and send a browser's Accept-Language. */
function request(answers: FakeAnswers, acceptLanguage: string | null): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  server.acceptLanguage = acceptLanguage;
  return client;
}

/** An API out of reach, as fetch says it: every request fails before any answer. */
function unreachable(acceptLanguage: string): string[] {
  const reached: string[] = [];
  server.client = createApiClient({
    address: "http://unreachable.invalid",
    fetch: (request) => {
      reached.push(new URL(request.url).pathname);
      return Promise.reject(new TypeError("fetch failed"));
    },
  });
  server.acceptLanguage = acceptLanguage;
  return reached;
}

/** The routes a request called, in order. */
function routes(client: FakeClient): string[] {
  return client.calls.map((call) => call.route);
}

beforeEach(() => {
  server.client = undefined;
});

describe("the language of a request", () => {
  it("is English for a browser asking for English at its first connection [WF-INTF-0160-A]", async () => {
    const client = request({ "GET /session": "session" }, "en-US,en;q=0.9");
    expect(await requestLanguage()).toEqual({ locale: "en", preference: "default" });
    // The browser decided: the installation is not asked.
    expect(routes(client)).toEqual(["GET /session"]);
  });

  it("is French for a browser asking for French [WF-INTF-0160-A]", async () => {
    request({ "GET /session": "session" }, "fr-FR,fr;q=0.9,en;q=0.8");
    expect(await requestLanguage()).toEqual({ locale: "fr", preference: "default" });
  });

  it("is the installation's for a browser asking for a language not offered [WF-INTF-0160-A]", async () => {
    const answers: FakeAnswers = {
      "GET /session": "session",
      [INSTALLATION]: "installation_english",
    };
    const client = request(answers, "de-DE,de;q=0.9");
    expect(await requestLanguage()).toEqual({ locale: "en", preference: "default" });
    expect(routes(client)).toEqual(["GET /session", INSTALLATION]);

    request({ "GET /session": "session", [INSTALLATION]: "installation" }, "de-DE,de;q=0.9");
    expect(await requestLanguage()).toEqual({ locale: "fr", preference: "default" });
  });

  it("is the one the account chose, whatever the browser asks for", async () => {
    const client = request({ "GET /session": "session_english" }, "fr-FR,fr;q=0.9");
    expect(await requestLanguage()).toEqual({ locale: "en", preference: "en" });
    expect(routes(client)).toEqual(["GET /session"]);
  });

  it("follows the browser for an account that never chose, and has no preference recorded", async () => {
    request({ "GET /session": "session_without_preferences" }, "en");
    expect(await requestLanguage()).toEqual({ locale: "en", preference: "default" });
  });

  it("lets a defect through rather than take it for an API out of reach", async () => {
    // No answer for GET /session: the fake client fails the call, and so the request.
    request({}, "en");
    await expect(requestLanguage()).rejects.toThrow("fakeClient: no answer for GET /session");
  });

  it("follows the browser without a session, on the sign-in page", async () => {
    const unauthorized = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;
    request({ "GET /session": unauthorized }, "en");
    expect(await requestLanguage()).toEqual({ locale: "en", preference: undefined });
  });

  it("follows the browser when the API cannot be reached", async () => {
    const reached = unreachable("en-GB,en;q=0.9");
    expect(await requestLanguage()).toEqual({ locale: "en", preference: undefined });
    expect(reached).toEqual(["/api/v1/session"]);
  });

  it("falls back on French when the installation cannot be reached", async () => {
    const reached = unreachable("de-DE,de;q=0.9");
    expect(await requestLanguage()).toEqual({ locale: "fr", preference: undefined });
    expect(reached).toEqual(["/api/v1/session", "/api/v1/installation"]);
  });

  it("falls back on the reference catalogue when the installation cannot be read", async () => {
    const unavailable = { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } } as const;
    request({ "GET /session": "session", [INSTALLATION]: unavailable }, null);
    expect(await requestLanguage()).toEqual({ locale: "fr", preference: "default" });
  });

  it("gives next-intl its language and the texts of that language", async () => {
    request({ "GET /session": "session_english" }, null);
    const config = await requestConfig();
    expect(config.locale).toBe("en");
    expect(config.messages).toBe(CATALOGUES.en);
    expect(config.messages.languageSelector.label).toBe("Language");
    expect(config.timeZone).toBe("UTC");
  });
});
