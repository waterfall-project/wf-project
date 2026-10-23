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
import { IdentifyRisk, ModifyRisk } from "./risk-commands";
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
const UPDATE = "PATCH /projects/{project_id}/risks/{risk_id}";
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
const UPDATED = example("risk_updated") as Risk;
// A counterfactual variant of `risk_created`: its provision frozen, as `update_provision` lists it for a risk
// that is no longer identified, the rest of the example kept.
const FROZEN: Risk = {
  ...CREATED,
  available_commands: CREATED.available_commands.map((offer) =>
    offer.command === "update_provision"
      ? { ...offer, is_available: false, missing_conditions: ["risk_identified"] }
      : offer,
  ),
};

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(
    {
      [CREATE]: { example: "risk_created", status: 201 },
      [UPDATE]: "risk_updated",
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

/** The command that modifies a risk, in French, over the detail of the risk. */
function modify(risk: Risk = CREATED, options: ProvisionOptions = OPTIONS) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <ModifyRisk projectId={PROJECT} risk={risk} options={options} />
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

describe("« Modifier » a risk", () => {
  it("opens the form on the risk as the detail shows it, and writes from its version, the provision as the form asks it", async () => {
    const client = serve();
    render(modify());
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const form = screen.getByRole("dialog", {
      name: "Modifier « Indisponibilité de la grue de levage »",
    });
    expect(within(form).getByRole("textbox", { name: "Libellé" })).toHaveValue(
      "Indisponibilité de la grue de levage",
    );
    expect(within(form).getByRole("textbox", { name: "Probabilité (%)" })).toHaveValue("20");
    expect(within(form).getByRole("combobox", { name: "Catégorie" })).toHaveValue(PROVISION[0]?.id);
    expect(within(form).getByRole("combobox", { name: "Tâche de la provision" })).toHaveValue(
      CREATED.provision_task?.node_id,
    );
    const probability = within(form).getByRole("textbox", { name: "Probabilité (%)" });
    await userEvent.clear(probability);
    await userEvent.type(probability, "25");
    await userEvent.selectOptions(within(form).getByRole("combobox", { name: "Catégorie" }), [
      CONTRACTUAL.id,
    ]);
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(client.calls[0]?.route).toBe(UPDATE);
    expect(client.calls[0]?.path).toBe(`/projects/${PROJECT}/risks/${CREATED.risk_id}`);
    expect(written(client)).toMatchObject({
      label: "Indisponibilité de la grue de levage",
      probability: "0.25",
      provision_cost_category_id: CONTRACTUAL.id,
      provision_subproject_id: null,
      provision_task_id: CREATED.provision_task?.node_id,
      lock_version: CREATED.lock_version,
    });
    expect(announced()).toContain("Risque « Indisponibilité de la grue de levage » modifié.");
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("writes the next modification from the version the answer brought, while the page read has not caught up", async () => {
    const client = serve();
    render(modify());
    /** One modification, saved with no change. */
    const save = async () => {
      await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
      await userEvent.click(
        within(screen.getByRole("dialog")).getByRole("button", { name: "Enregistrer" }),
      );
      await vi.waitFor(() => {
        expect(screen.queryByRole("dialog")).toBeNull();
      });
    };
    await save();
    await save();
    expect(client.calls.map(({ body }) => (body as { lock_version: number }).lock_version)).toEqual(
      [CREATED.lock_version, UPDATED.lock_version],
    );
  });

  it("shows the provision fixed when the risk lists `update_provision` unavailable, says what it lacks, and sends none of it", async () => {
    const client = serve();
    render(modify(FROZEN));
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const form = screen.getByRole("dialog", {
      name: "Modifier « Indisponibilité de la grue de levage »",
    });
    const category = within(form).getByRole("textbox", { name: "Catégorie" });
    expect(category).toHaveAttribute("readonly");
    expect(category).toHaveAccessibleDescription(/^Condition non remplie\s: risque identifié\.$/);
    expect(within(form).getByRole("textbox", { name: "Tâche de la provision" })).toHaveAttribute(
      "readonly",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    const body = written(client) as Record<string, unknown>;
    expect(Object.keys(body).filter((key) => key.startsWith("provision_"))).toEqual([]);
    expect(body).toMatchObject({ lock_version: CREATED.lock_version, probability: "0.2" });
  });

  it("keeps the category deactivated since the risk was declared among the choices, said so, and asks another only when the user chooses it", async () => {
    const client = serve();
    const deactivated: Risk = { ...CREATED, provision_cost_category_is_active: false };
    render(modify(deactivated, { ...OPTIONS, categories: [CONTRACTUAL] }));
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const form = screen.getByRole("dialog");
    const category = within(form).getByRole("combobox", { name: "Catégorie" });
    expect(category).toHaveValue(CREATED.provision_cost_category_id);
    expect(within(category).getByRole("option", { name: /\(désactivée\)$/ })).toBeInTheDocument();
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    // Unchanged, the category is sent as it is: the server accepts it (`INACTIVE_REFERENCE_OBJECT`
    // only vaut quand la valeur change la catégorie).
    expect(written(client)).toMatchObject({
      provision_cost_category_id: CREATED.provision_cost_category_id,
    });
  });

  it("keeps the task the risk holds among the choices when the main structure no longer lists it, rather than moving the line", async () => {
    const client = serve();
    render(
      modify(CREATED, {
        ...OPTIONS,
        tasks: TASKS.filter(({ id }) => id !== CREATED.provision_task?.node_id),
      }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const form = screen.getByRole("dialog");
    expect(within(form).getByRole("combobox", { name: "Tâche de la provision" })).toHaveValue(
      CREATED.provision_task?.node_id,
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(written(client)).toMatchObject({ provision_task_id: CREATED.provision_task?.node_id });
  });

  it("offers nothing to modify a risk occurred, and says why when it lists the modification unavailable", () => {
    const occurred = example("risk_occurred_detail") as Risk;
    render(modify(occurred));
    const command = screen.getByRole("button", { name: "Modifier" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(/^Condition non remplie\s: risque non survenu\.$/);
  });

  it("offers no modification to a caller whose risk lists none", () => {
    render(modify({ ...CREATED, available_commands: [] }));
    expect(screen.queryByRole("button", { name: "Modifier" })).toBeNull();
  });

  it("keeps the modification waiting while a write of the dialog closed is under way, then writes from the version the answer brings (défaut n° 24)", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    render(modify());
    const command = () => screen.getByRole("button", { name: "Modifier" });
    await userEvent.click(command());
    const form = screen.getByRole("dialog");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(command()).toHaveFocus();
    expect(command()).toHaveAttribute("aria-disabled", "true");
    expect(command()).toHaveAccessibleDescription("Enregistrement en cours…");
    await userEvent.click(command());
    expect(screen.queryByRole("dialog")).toBeNull();
    release();
    await vi.waitFor(() => {
      expect(command()).not.toHaveAttribute("aria-disabled");
    });
    await userEvent.click(command());
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Enregistrer" }),
    );
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.body).toMatchObject({ lock_version: UPDATED.lock_version });
  });
});
