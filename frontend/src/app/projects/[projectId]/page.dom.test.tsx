// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of a project without a revision, audited for accessibility (WF-IHM-0100): the one
 * screen of the table of the pages that the paths of the browser cannot reach, the fake back
 * serving every project as the witness, which has revisions (`LEADING_SCREENS`, `e2e/routes.ts`).
 * The page is read on the server, as in its own tests, and rendered into a document.
 */
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import ProjectPage from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => `/projects/${PRICING}`,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

// The project in pricing, without a revision (`project_pricing.json`).
const PRICING = "01926f3a-7c00-7000-8000-000000000002";

beforeEach(() => {
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project_pricing",
    "GET /projects/{project_id}/revisions": "revisions_empty",
  };
});

describe("the screen of a project without a revision", () => {
  it("breaks none of the rules of accessibility, its encart and its imports shown [WF-IHM-0100-A]", async () => {
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PRICING }),
      searchParams: Promise.resolve({}),
    });
    const { container } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        {page}
      </NextIntlClientProvider>,
    );
    await expectAccessible(container);
  });
});
