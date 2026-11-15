// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lifecycle of a project, rendered in a document (US-2130): a screen of consultation in the
 * airy column, the next state and the history of the states each in a card; the exits of the
 * lifecycle stay at the right of the title, outlined, none filled (`expectCommandRule`).
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SCREEN } from "@/components/shell/page-header";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectCommandRule } from "@/test/command-rule";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import LifecyclePage from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects/p/lifecycle",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1400);
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/next-state": "next_state",
    "GET /projects/{project_id}/state-transitions": "state_transitions",
  };
});

describe("the lifecycle, rendered", () => {
  it("sets the next state and the history of the states each in its card, the exits staying outlined at the right of the title [WF-IHM-0090-A]", async () => {
    const page = await LifecyclePage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: Promise.resolve({}),
    });
    const { container } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        {page}
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("main")).toHaveClass(...SCREEN.airy.split(" "));
    for (const title of ["Prochain état", "Historique des états"]) {
      expect(screen.getByRole("region", { name: title })).toHaveAttribute(
        "data-slot",
        "section-card",
      );
    }
    expect(container.querySelectorAll("button.bg-primary, a.bg-primary")).toHaveLength(0);
    expectCommandRule(container);
  });
});
