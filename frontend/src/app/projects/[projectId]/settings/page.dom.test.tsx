// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import SettingsPage from "./page";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => `/projects/${PROJECT}/settings`,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

beforeEach(() => {
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project_created",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/contributors": "contributors",
    "GET /projects/{project_id}/contributors/suggestions": "contributor_suggestions",
    "GET /projects/{project_id}/work-breakdown": "work_breakdown",
  };
});

describe("the settings of a project, rendered", () => {
  // The console is watched by the setup of the DOM tests: a duplicate key of React, among the
  // children of the page, is an error written on it and fails the test.
  it("renders the generation and the identity side by side without a warning of React, on a project without revision [WF-PRJ-0030-A]", async () => {
    const page = await SettingsPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: Promise.resolve({ start: "skeleton" }),
    });
    render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        {page}
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("button", { name: "Generate the planning" })).toBeVisible();
  });
});
