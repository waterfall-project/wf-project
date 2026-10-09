// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ApiClient } from "@/api/client";
import type { CommandOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { costRow, type CostRow } from "./cost-grid";
import { CostLineScope } from "./cost-line-scope";
import { CostsGrid } from "./costs-grid";

// The server of Next, as far as the screen needs it: the fake back, the page rendered again, the
// address it reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATHNAME = "/projects/p/revisions/r/actual-costs";

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Project = components["schemas"]["Project"];
type ActualCostLine = components["schemas"]["ActualCostLine"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const SCOPE = "PUT /projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope";

/** The lines of the witness, as the page hands them to the grid. */
const COSTS = example("actual_costs") as {
  items: ActualCostLine[];
  totals: components["schemas"]["ActualCostTotals"];
  meta: { passthrough_columns: string[] };
};

/** A line of the witness as the grid reads it, by its number of document. */
function line(document: string): CostRow {
  const found = COSTS.items.find((item) => item.document_number === document);
  if (found === undefined) {
    throw new Error(`no line ${document}`);
  }
  return costRow(found);
}

/** The offer of the exclusion a project of the contract lists, by the name of its example. */
function offerOf(name: "project" | "project_completed"): CommandOffer {
  const project = example(name) as Project;
  const offer = project.available_commands.find((each) => each.command === "exclude_cost_lines");
  if (offer === undefined) {
    throw new Error(`${name} lists no exclusion`);
  }
  return offer;
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A part of the screen, in French. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  refresh.mockReset();
  router.push.mockReset();
  page.search = "";
  // A window the grid lays its rows in: six lines and their head fit in it.
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the place of a line in the tracked scope", () => {
  it("excludes a line from the list with the reason written, and the page reads the totals anew [WF-CRE-0040-A]", async () => {
    const client = serve({ [SCOPE]: "actual_cost_excluded" });
    const cables = line("FA-2026-0412");
    const { container } = render(
      inFrench(<CostLineScope projectId={PROJECT} line={cables} offer={offerOf("project")} />),
    );
    const section = screen.getByRole("region", { name: "Ligne FA-2026-0412" });
    expect(section).toHaveTextContent("Suivie");
    await userEvent.type(
      screen.getByLabelText("Motif de l’exclusion"),
      "  Câbles d'un autre projet, à réimputer ",
    );
    await userEvent.click(screen.getByRole("button", { name: "Exclure du périmètre suivi" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // The server excludes the line; the page rendered again reads it, and the three totals the
    // server keeps: the front counts none of them.
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [
        `/projects/${PROJECT}/actual-costs/${cables.cost_line_id}/tracked-scope`,
        { is_in_tracked_scope: false, reason: "Câbles d'un autre projet, à réimputer" },
      ],
    ]);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await expectAccessible(container);
  });

  it("forgets the reason written once the server says the line moved", async () => {
    serve({});
    const cables = line("FA-2026-0412");
    const scope = (shown: CostRow) =>
      inFrench(<CostLineScope projectId={PROJECT} line={shown} offer={offerOf("project")} />);
    const { rerender } = render(scope(cables));
    await userEvent.type(screen.getByLabelText("Motif de l’exclusion"), "Hors budget");
    // The page read anew after the exclusion, then after a reinstatement.
    rerender(scope(costRow(example("actual_cost_excluded") as ActualCostLine)));
    expect(screen.getByRole("region", { name: "Ligne FA-2026-0412" })).toHaveTextContent(
      "Exclue du périmètre suivi : Câbles d'un autre projet, à réimputer",
    );
    rerender(scope(cables));
    expect(screen.getByLabelText("Motif de l’exclusion")).toHaveValue("");
  });

  it("excludes a line without a reason when none is written", async () => {
    const client = serve({ [SCOPE]: "actual_cost_excluded" });
    render(
      inFrench(
        <CostLineScope
          projectId={PROJECT}
          line={line("FA-2026-0412")}
          offer={offerOf("project")}
        />,
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Exclure du périmètre suivi" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toEqual({ is_in_tracked_scope: false, reason: null });
  });

  it("says why an excluded line is excluded, and reinstates it", async () => {
    const client = serve({ [SCOPE]: "actual_cost_reinstated" });
    const reception = line("FA-2026-0295");
    render(
      inFrench(<CostLineScope projectId={PROJECT} line={reception} offer={offerOf("project")} />),
    );
    expect(screen.getByRole("region", { name: "Ligne FA-2026-0295" })).toHaveTextContent(
      "Exclue du périmètre suivi : Réception du client, non budgétée",
    );
    expect(screen.queryByLabelText("Motif de l’exclusion")).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Réintégrer dans le périmètre suivi" }),
    );
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(client.calls[0]?.body).toEqual({ is_in_tracked_scope: true, reason: null });
  });

  it("offers the command unavailable with what it lacks on a project that ended, and runs nothing", async () => {
    const client = serve({});
    render(
      inFrench(
        <CostLineScope
          projectId={PROJECT}
          line={line("FA-2026-0412")}
          offer={offerOf("project_completed")}
        />,
      ),
    );
    const command = screen.getByRole("button", { name: "Exclure du périmètre suivi" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(/projet/i);
    await userEvent.click(command);
    expect(client.calls).toEqual([]);
  });

  it("tells the refusal of the server, and renders nothing again", async () => {
    serve({ [SCOPE]: { problem: { code: "NOT_FOUND", status: 404 } } });
    render(
      inFrench(
        <CostLineScope
          projectId={PROJECT}
          line={line("FA-2026-0412")}
          offer={offerOf("project")}
        />,
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Exclure du périmètre suivi" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Introuvable : cet élément n’existe pas, ou vous n’y avez pas accès.",
    );
    expect(refresh).not.toHaveBeenCalled();
  });

  it("closes, the rest of the address kept", async () => {
    page.search = "line=x&in_tracked_scope=true";
    render(
      inFrench(
        <CostLineScope
          projectId={PROJECT}
          line={line("FA-2026-0412")}
          offer={offerOf("project")}
        />,
      ),
    );
    await userEvent.click(screen.getByRole("link", { name: "Fermer la ligne" }));
    expect(router.push).toHaveBeenCalledWith(`${PATHNAME}?in_tracked_scope=true`, {
      scroll: false,
    });
  });
});

describe("the number of a line in the grid", () => {
  const costs = {
    items: COSTS.items.map(costRow),
    totals: COSTS.totals,
    kept: COSTS.meta.passthrough_columns,
  };
  const query = { sort: undefined, search: undefined };

  it("shows the line where the user may exclude it, a link out of the tabulation, the line shown marked", () => {
    const cables = line("FA-2026-0412");
    page.search = `line=${cables.cost_line_id}`;
    render(inFrench(<CostsGrid costs={costs} query={query} preferences={undefined} linked />));
    const grid = screen.getByRole("grid", { name: "Coûts réels" });
    const link = within(grid).getByRole("link", { name: "FA-2026-0412" });
    expect(link).toHaveAttribute("href", `${PATHNAME}?line=${cables.cost_line_id}`);
    expect(link).toHaveAttribute("tabindex", "-1");
    expect(link).toHaveAttribute("aria-current", "true");
    expect(within(grid).getByRole("link", { name: "FA-2026-0295" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("is a plain text where the user may not exclude it", () => {
    render(inFrench(<CostsGrid costs={costs} query={query} preferences={undefined} />));
    const grid = screen.getByRole("grid", { name: "Coûts réels" });
    expect(within(grid).getByText("FA-2026-0412")).toBeInTheDocument();
    expect(within(grid).queryByRole("link", { name: "FA-2026-0412" })).not.toBeInTheDocument();
  });
});
