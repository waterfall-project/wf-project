// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import type { ProjectPage, ProjectRow } from "./portfolio-grid";
import { PilotHealthView, PortfolioRisksView } from "./portfolio-views";
import { ProjectsGrid } from "./projects-grid";

// What the grid reads of the server of Next and of the address.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
vi.mock("@/api/server", () => ({ serverClient: () => undefined }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/portfolio/projects",
  useSearchParams: () => new URLSearchParams(""),
}));

type Schemas = components["schemas"];

const LIST = example("volume/portfolio_projects") as {
  items: ProjectRow[];
  meta: ProjectPage;
};
const HEALTH = example("pilot_health") as Schemas["PilotHealth"];
const RISKS = example("volume/portfolio_risks") as Schemas["PortfolioRisks"];

/** A part of the screen, in French, under the address of the screen. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1400);
});

describe("a project the caller cannot open, named without a link [US-2760] [WF-PTF-0030-A]", () => {
  it("names it in the list of the projects, and links the projects the caller can open", () => {
    const closed = LIST.items.find((item) => !item.can_open);
    const open = LIST.items.find((item) => item.can_open);
    if (closed === undefined || open === undefined) {
      throw new Error("the examples hold a project the caller cannot open, and one they can");
    }
    render(
      inFrench(
        <ProjectsGrid
          projects={[closed, open]}
          page={LIST.meta}
          query={{ sort: undefined, search: undefined, size: undefined }}
          preferences={undefined}
        />,
      ),
    );
    const grid = screen.getByRole("grid", { name: "Projets du portefeuille" });
    expect(within(grid).getByText(closed.label)).toBeVisible();
    expect(within(grid).queryByRole("link", { name: closed.label })).toBeNull();
    expect(within(grid).getByRole("link", { name: open.label })).toHaveAttribute(
      "href",
      `/projects/${open.project_id}`,
    );
  });

  it("names it in the heaviest risks, and links the other projects", () => {
    const first = RISKS.heaviest[0];
    const other = RISKS.heaviest.find((risk) => risk.project_id !== first?.project_id);
    if (first === undefined || other === undefined) {
      throw new Error("the examples hold heavy risks of two projects");
    }
    const risks: Schemas["PortfolioRisks"] = {
      ...RISKS,
      heaviest: RISKS.heaviest.map((risk) => ({
        ...risk,
        can_open: risk.project_id !== first.project_id,
      })),
    };
    render(inFrench(<PortfolioRisksView risks={risks} />));
    const table = screen.getByRole("table", { name: "Risques les plus lourds" });
    expect(within(table).getAllByText(first.project_label).length).toBeGreaterThan(0);
    expect(within(table).queryByRole("link", { name: first.project_label })).toBeNull();
    expect(
      within(table).getAllByRole("link", { name: other.project_label }).length,
    ).toBeGreaterThan(0);
  });

  it("names it in the signals of the pilot health, and links the others", () => {
    const closed = HEALTH.signals.find((signal) => !signal.can_open);
    if (closed === undefined) {
      throw new Error("the examples hold a signal of a project the caller cannot open");
    }
    render(inFrench(<PilotHealthView health={HEALTH} />));
    const table = screen.getByRole("table", { name: "Signaux de santé du pilotage" });
    expect(within(table).getAllByText(closed.project_label).length).toBeGreaterThan(0);
    expect(within(table).queryByRole("link", { name: closed.project_label })).toBeNull();
    expect(within(table).getAllByRole("link")).toHaveLength(
      HEALTH.signals.filter((signal) => signal.can_open).length,
    );
  });
});

describe("the views of the portfolio carry no command of entry [US-2760]", () => {
  it("offers no field to type in on the risks nor on the pilot health", () => {
    render(
      inFrench(
        <>
          <PortfolioRisksView risks={RISKS} />
          <PilotHealthView health={HEALTH} />
        </>,
      ),
    );
    for (const role of ["textbox", "spinbutton", "combobox", "checkbox", "switch"] as const) {
      expect(screen.queryAllByRole(role)).toHaveLength(0);
    }
  });
});
