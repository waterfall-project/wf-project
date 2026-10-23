// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { CommandOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  held,
  type Problem,
} from "@/test/fixtures";

import type { ProvisionOptions } from "./provision-choices";
import { IdentifyRisk } from "./risk-commands";
import type { Risk } from "./risk-detail";

// The server of Next, as far as the commands need it: the fake back, the page read anew once a write
// is answered, the address it reads and the router it leads by.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// A write whose server action rejects once `until` settles — the API out of reach, as `fetch`
// rejects in the browser —; none, and the action asks the fake back.
const failing = vi.hoisted((): { until: Promise<void> | undefined } => ({ until: undefined }));
vi.mock("@/api/actions/risks", async (original) => {
  const actual = await original<typeof import("@/api/actions/risks")>();
  return {
    ...actual,
    writeRisk: async (...asked: Parameters<typeof actual.writeRisk>) => {
      if (failing.until === undefined) {
        return actual.writeRisk(...asked);
      }
      await failing.until;
      throw new TypeError("Failed to fetch");
    },
  };
});
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/r/risks",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
// The estimate of the revision, its reading context carried: the structure of the risk is added.
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate?as_of=2026-03-01`;
const CREATE = "POST /projects/{project_id}/risks";
const AVAILABLE: CommandOffer = { is_available: true, missing_conditions: [] };

type Choices = ProvisionOptions["categories"];
interface CostCategories {
  items: { cost_category_id: string; label: string; cost_type_kind: string }[];
}

// The category of provision of the reference data of the witness, as the form offers it.
const PROVISION = (example("volume/cost_categories") as CostCategories).items
  .filter((category) => category.cost_type_kind === "provision")
  .map(({ cost_category_id: id, label }) => ({ id, label }));
const ONE: Choices = PROVISION;
// A counterfactual variant: the installation distinguishes a second category of the type.
const CONTRACTUAL = { id: "01926f3a-7c00-7000-8000-000000000405", label: "Aléas contractuels" };
const TWO: Choices = [...ONE, CONTRACTUAL];
const SUBPROJECTS = (example("subprojects") as { subproject_id: string; label: string }[]).map(
  ({ subproject_id: id, label }) => ({ id, label }),
);
const TASKS = (
  example("nodes") as {
    items: { node_id: string; kind: string; task?: { label: string } | null }[];
  }
).items.flatMap(({ node_id: id, kind, task }) =>
  kind === "task" && task ? [{ id, label: task.label }] : [],
);
const OPTIONS: ProvisionOptions = { categories: TWO, subprojects: SUBPROJECTS, tasks: TASKS };
const ONLY_ONE: ProvisionOptions = { ...OPTIONS, categories: ONE };

const CREATED = example("risk_created") as Risk;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(
    {
      [CREATE]: { example: "risk_created", status: 201 },
      ...answers,
    },
    timing,
  );
  server.client = client;
  return client;
}

/** The command that identifies a risk, in French, as the revision lists `declare_risk`. */
function identify(
  offer: CommandOffer | null = AVAILABLE,
  options: ProvisionOptions = OPTIONS,
  estimate: string | null = ESTIMATE,
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <IdentifyRisk
          projectId={PROJECT}
          offer={offer ?? undefined}
          options={options}
          estimate={estimate ?? undefined}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The body of the one write the commands made. */
function written(client: FakeClient): unknown {
  return client.calls.map(({ body }) => body)[0];
}

/** Fill the fields every declaration requires. */
async function fill(form: HTMLElement, label: string, probability: string) {
  await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), label);
  await userEvent.type(within(form).getByRole("textbox", { name: "Probabilité (%)" }), probability);
}

/** What the regions of the commands announce. */
function announced(): (string | null)[] {
  return screen.getAllByRole("status").map((status) => status.textContent);
}

/** The command that identifies a risk. */
function identifyCommand(): HTMLElement {
  return screen.getByRole("button", { name: "Identifier un risque" });
}

beforeEach(() => {
  sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  failing.until = undefined;
  vi.restoreAllMocks();
  refresh.mockClear();
  router.push.mockClear();
  router.refresh.mockClear();
});

describe("« Identifier un risque »", () => {
  it.each([
    ["two categories, asks which carries the provision", TWO, true],
    ["a single one, does not ask", ONE, false],
  ] satisfies [string, Choices, boolean][])(
    "with %s, and writes the risk before opening its own estimate [WF-RIS-0010-A]",
    async (_name, categories, asks) => {
      const client = serve();
      const { container } = render(identify(AVAILABLE, { ...OPTIONS, categories }));
      await userEvent.click(identifyCommand());
      const form = screen.getByRole("dialog", { name: "Identifier un risque" });
      const category = within(form).queryByRole("combobox", { name: "Catégorie" });
      expect(category !== null).toBe(asks);
      await fill(form, " Indisponibilité de la grue ", "20");
      if (category !== null) {
        // The category is required before anything is asked, and takes the focus.
        await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
        expect(category).toHaveAccessibleDescription("Une valeur est requise.");
        expect(category).toHaveFocus();
        expect(client.calls).toEqual([]);
        await userEvent.selectOptions(category, CONTRACTUAL.id);
      }
      await expectAccessible(container);
      await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
      await vi.waitFor(() => {
        expect(router.push).toHaveBeenCalledOnce();
      });
      expect(client.calls).toHaveLength(1);
      expect(client.calls[0]?.path).toBe(`/projects/${PROJECT}/risks`);
      expect(written(client)).toEqual({
        label: "Indisponibilité de la grue",
        description: null,
        mitigation_notes: null,
        // Entered as a percentage, sent as the ratio of the contract.
        probability: "0.2",
        ...(asks ? { provision_cost_category_id: CONTRACTUAL.id } : {}),
        provision_subproject_id: null,
        provision_task_id: null,
      });
      expect(screen.queryByRole("dialog")).toBeNull();
    },
  );

  it("opens the own estimate of the risk in the grid of the estimate, the reading context kept, once it is declared", async () => {
    serve();
    render(identify());
    await userEvent.click(identifyCommand());
    const form = screen.getByRole("dialog", { name: "Identifier un risque" });
    await fill(form, "Retard de livraison", "40");
    await userEvent.selectOptions(within(form).getByRole("combobox", { name: "Catégorie" }), [
      CONTRACTUAL.id,
    ]);
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(router.push).toHaveBeenCalledWith(`${ESTIMATE}&structure=${CREATED.structure_id}`);
    });
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("says the risk declared and stays where it is for a session that may not read the estimate", async () => {
    serve();
    render(identify(AVAILABLE, ONLY_ONE, null));
    await userEvent.click(identifyCommand());
    const form = screen.getByRole("dialog", { name: "Identifier un risque" });
    await fill(form, "Retard de livraison", "40");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(announced()).toContain("Risque « Indisponibilité de la grue de levage » identifié.");
    expect(router.push).not.toHaveBeenCalled();
    // The command is back where it was, with the focus.
    expect(identifyCommand()).toHaveFocus();
  });

  it("offers the declaration unavailable, described by the lack of an active category of provision, and opens nothing [WF-RIS-0010-A]", async () => {
    const client = serve();
    render(
      identify({ is_available: false, missing_conditions: ["active_provision_category"] }, OPTIONS),
    );
    const command = identifyCommand();
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(
      /^Condition non remplie\s: une catégorie de provision pour risques active\.$/,
    );
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
  });

  it("offers the declaration unavailable, described by the lack of a task, on a revision without one [WF-RIS-0010-A]", async () => {
    const client = serve();
    render(identify({ is_available: false, missing_conditions: ["at_least_one_task"] }, OPTIONS));
    const command = identifyCommand();
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(/^Condition non remplie\s: au moins une tâche\.$/);
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
  });

  it("offers nothing to a caller whose revision lists no declaration", () => {
    render(identify(null));
    expect(screen.queryByRole("button", { name: "Identifier un risque" })).toBeNull();
  });

  it.each([
    [
      "an active category of provision [WF-RIS-0010-A]",
      "risk_without_provision_category",
      /Condition non remplie\s: une catégorie de provision pour risques active\./,
    ],
    [
      "a task [WF-RIS-0010-A]",
      "risk_without_task",
      /Condition non remplie\s: au moins une tâche\./,
    ],
  ] satisfies [string, string, RegExp][])(
    "tells the refusal of the server lacking %s under the form, which stays open with its entry",
    async (_lacking, problem, said) => {
      const client = serve({
        [CREATE]: { problem: example(problem) as Problem & { status: 409 } },
      });
      render(identify());
      await userEvent.click(identifyCommand());
      const form = screen.getByRole("dialog", { name: "Identifier un risque" });
      await fill(form, "Retard de livraison", "40");
      await userEvent.selectOptions(within(form).getByRole("combobox", { name: "Catégorie" }), [
        CONTRACTUAL.id,
      ]);
      await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
      expect(await within(form).findByRole("alert")).toHaveTextContent(said);
      expect(client.calls).toHaveLength(1);
      expect(within(form).getByRole("textbox", { name: "Libellé" })).toHaveValue(
        "Retard de livraison",
      );
      expect(router.push).not.toHaveBeenCalled();
    },
  );

  it("says at their fields the category and the sub-project the server refuses, and gives the focus to the first", async () => {
    serve({
      [CREATE]: { problem: example("risk_provision_refused") as Problem & { status: 422 } },
    });
    render(identify());
    await userEvent.click(identifyCommand());
    const form = screen.getByRole("dialog", { name: "Identifier un risque" });
    await fill(form, "Retard de livraison", "40");
    await userEvent.selectOptions(within(form).getByRole("combobox", { name: "Catégorie" }), [
      CONTRACTUAL.id,
    ]);
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const category = await within(form).findByRole("combobox", { name: "Catégorie" });
    await vi.waitFor(() => {
      expect(category).toHaveAccessibleDescription(
        "La provision d’un risque porte une catégorie de type provision pour risques.",
      );
    });
    expect(category).toHaveFocus();
    expect(within(form).getByRole("combobox", { name: "Sous-projet" })).toHaveAccessibleDescription(
      "Sous-projet inconnu.",
    );
  });

  it("keeps the command waiting while a write of the dialog closed is under way, tells the risk declared once answered, and leads nowhere (défaut n° 24)", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    render(identify(AVAILABLE, ONLY_ONE));
    await userEvent.click(identifyCommand());
    const form = screen.getByRole("dialog", { name: "Identifier un risque" });
    await fill(form, "Retard de livraison", "40");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    // Opened anew, the form would send a second declaration of the same risk: the command waits.
    expect(identifyCommand()).toHaveFocus();
    expect(identifyCommand()).toHaveAttribute("aria-disabled", "true");
    expect(identifyCommand()).toHaveAttribute("aria-busy", "true");
    expect(identifyCommand()).toHaveAccessibleDescription("Enregistrement en cours…");
    await userEvent.click(identifyCommand());
    expect(screen.queryByRole("dialog")).toBeNull();
    release();
    await vi.waitFor(() => {
      expect(announced()).toContain("Risque « Indisponibilité de la grue de levage » identifié.");
    });
    // The user closed the form: the answer does not take him away.
    expect(router.push).not.toHaveBeenCalled();
    await vi.waitFor(() => {
      expect(identifyCommand()).not.toHaveAttribute("aria-disabled");
    });
  });

  it("frees the command, and tells the service out of reach, when the write of the dialog closed is rejected", async () => {
    const { timing, until, release } = held();
    failing.until = until;
    serve({}, timing);
    render(identify(AVAILABLE, ONLY_ONE));
    await userEvent.click(identifyCommand());
    const form = screen.getByRole("dialog", { name: "Identifier un risque" });
    await fill(form, "Retard de livraison", "40");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(identifyCommand()).toHaveAttribute("aria-disabled", "true");
    release();
    expect(await screen.findByText(/Le service est injoignable/)).toBeInTheDocument();
    await vi.waitFor(() => {
      expect(identifyCommand()).not.toHaveAttribute("aria-disabled");
    });
    expect(router.push).not.toHaveBeenCalled();
    await userEvent.click(identifyCommand());
    expect(screen.getByRole("dialog", { name: "Identifier un risque" })).toBeVisible();
  });

  it("tells the service out of reach under the form open, which stays open with its entry", async () => {
    const { until, release } = held();
    failing.until = until;
    serve();
    render(identify(AVAILABLE, ONLY_ONE));
    await userEvent.click(identifyCommand());
    const form = screen.getByRole("dialog", { name: "Identifier un risque" });
    await fill(form, "Retard de livraison", "40");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    release();
    expect(await within(form).findByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(within(form).getByRole("textbox", { name: "Libellé" })).toHaveValue(
      "Retard de livraison",
    );
    expect(router.push).not.toHaveBeenCalled();
  });

  it("gives the focus back to the command when the form is cancelled", async () => {
    serve();
    render(identify());
    await userEvent.click(identifyCommand());
    await userEvent.click(
      within(screen.getByRole("dialog", { name: "Identifier un risque" })).getByRole("button", {
        name: "Annuler",
      }),
    );
    await vi.waitFor(() => {
      expect(identifyCommand()).toHaveFocus();
    });
  });
});
