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
import { type Risk, RiskDetail } from "./risk-detail";

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
// The risk dismissed of the contract: `update` available, `update_provision` unavailable (the risk is no
// longer identified), and no task for its provision.
const FROZEN: Risk = (() => {
  const found = (example("risks") as { items: Risk[] }).items.find(
    ({ state }) => state === "dismissed",
  );
  if (found === undefined) {
    throw new Error("the contract lists no risk dismissed");
  }
  return found;
})();

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

const OTHER: Risk = {
  ...CREATED,
  risk_id: "01926f3a-7c00-7000-8000-000000000799",
  label: "Retard de livraison des armoires",
};

/** The detail of a risk, as the screen of the risks hands it, in French. */
function detail(risk: Risk) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <RiskDetail risk={risk} reviews={[]} projectId={PROJECT} options={OPTIONS} />
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
      // The texts are multiline: the break of the line is written as typed.
      await userEvent.type(
        within(form).getByRole("textbox", { name: "Description" }),
        "Grue immobilisée{Enter}deux semaines au plus",
      );
      await userEvent.type(
        within(form).getByRole("textbox", { name: "Actions de mitigation" }),
        "Louer une grue de secours",
      );
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
        description: "Grue immobilisée\ndeux semaines au plus",
        mitigation_notes: "Louer une grue de secours",
        // Entered as a percentage, sent as the ratio of the contract.
        probability: "0.2",
        ...(asks ? { provision_cost_category_id: CONTRACTUAL.id } : {}),
        provision_subproject_id: null,
        provision_task_id: null,
      });
      expect(screen.queryByRole("dialog")).toBeNull();
    },
  );

  it.each([
    [
      "tasks",
      { ...ONLY_ONE, tasks: [] },
      "Tâche de la provision",
      "provision_task_id",
      "Sous-projet",
    ],
    [
      "sub-projects",
      { ...ONLY_ONE, subprojects: [] },
      "Sous-projet",
      "provision_subproject_id",
      "Tâche de la provision",
    ],
  ] satisfies [string, ProvisionOptions, string, string, string][])(
    "opens the form without the field of the %s the session may not read, and sends it without that field",
    async (_name, options, absent, key, present) => {
      const client = serve();
      render(identify(AVAILABLE, options));
      await userEvent.click(identifyCommand());
      const form = screen.getByRole("dialog", { name: "Identifier un risque" });
      expect(within(form).queryByRole("combobox", { name: absent })).toBeNull();
      expect(within(form).getByRole("combobox", { name: present })).toBeInTheDocument();
      await fill(form, "Retard de livraison", "40");
      await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
      await vi.waitFor(() => {
        expect(client.calls).toHaveLength(1);
      });
      const body = written(client) as Record<string, unknown>;
      expect(body).not.toHaveProperty(key);
      expect(body).toMatchObject({ label: "Retard de livraison", probability: "0.4" });
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

  it("says the bound of the probability at its field in percentages, the server naming it in the ratio [WF-RIS-0010-A]", async () => {
    serve({
      [CREATE]: {
        problem: example("risk_probability_out_of_range") as Problem & { status: 422 },
      },
    });
    render(identify(AVAILABLE, ONLY_ONE));
    await userEvent.click(identifyCommand());
    const form = screen.getByRole("dialog", { name: "Identifier un risque" });
    await fill(form, "Retard de livraison", "120");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    const probability = await within(form).findByRole("textbox", { name: "Probabilité (%)" });
    await vi.waitFor(() => {
      expect(probability).toHaveAccessibleDescription(/100/);
    });
    expect(probability).not.toHaveAccessibleDescription(/\b1\b/);
    expect(probability).toHaveFocus();
  });

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

  const CLOSED = [
    [
      "tells the risk declared once answered, and leads nowhere",
      "success",
      /Risque « Indisponibilité de la grue de levage » identifié\./,
    ],
    [
      "tells the service out of reach once the action is rejected",
      "rejected",
      /Le service est injoignable/,
    ],
    [
      "tells the condition the server finds unmet once it refuses",
      "refused",
      /Condition non remplie\s: au moins une tâche\./,
    ],
  ] satisfies [string, "success" | "rejected" | "refused", RegExp][];

  it.each(CLOSED)(
    "keeps the command waiting while a write of the dialog closed is under way, %s, then frees it (défaut n° 24)",
    async (_name, kind, said) => {
      const { timing, until, release } = held();
      if (kind === "rejected") {
        failing.until = until;
      }
      const client = serve(
        kind === "refused"
          ? { [CREATE]: { problem: example("risk_without_task") as Problem & { status: 409 } } }
          : {},
        timing,
      );
      render(identify(AVAILABLE, ONLY_ONE));
      await userEvent.click(identifyCommand());
      const form = screen.getByRole("dialog", { name: "Identifier un risque" });
      await fill(form, "Retard de livraison", "40");
      await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
      if (kind !== "rejected") {
        await vi.waitFor(() => {
          expect(client.calls).toHaveLength(1);
        });
      }
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
      expect(await screen.findByText(said)).toBeInTheDocument();
      // The user closed the form: the answer does not take him away, nor does it open it again.
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(router.push).not.toHaveBeenCalled();
      await vi.waitFor(() => {
        expect(identifyCommand()).not.toHaveAttribute("aria-disabled");
      });
      expect(identifyCommand()).not.toHaveAttribute("aria-busy", "true");
      if (kind !== "success") {
        await userEvent.click(identifyCommand());
        expect(screen.getByRole("dialog", { name: "Identifier un risque" })).toBeVisible();
      }
    },
  );

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
      name: "Modifier « Indisponibilité de l'automaticien »",
    });
    const category = within(form).getByRole("textbox", { name: "Catégorie" });
    expect(category).toHaveAttribute("readonly");
    expect(category).toHaveAccessibleDescription(/^Condition non remplie\s: risque identifié\.$/);
    const task = within(form).getByRole("textbox", { name: "Tâche de la provision" });
    expect(task).toHaveAttribute("readonly");
    expect(task).toHaveValue("—");
    const subproject = within(form).getByRole("textbox", { name: "Sous-projet" });
    expect(subproject).toHaveAttribute("readonly");
    expect(subproject).toHaveValue("Hors sous-projet");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    const body = written(client) as Record<string, unknown>;
    expect(Object.keys(body).filter((key) => key.startsWith("provision_"))).toEqual([]);
    expect(body).toMatchObject({ lock_version: FROZEN.lock_version, probability: "0.05" });
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
  it.each([
    [
      "tasks",
      (options: ProvisionOptions): ProvisionOptions => ({ ...options, tasks: [] }),
      "Tâche de la provision",
      "provision_task_id",
      "Sous-projet",
    ],
    [
      "sub-projects",
      (options: ProvisionOptions): ProvisionOptions => ({ ...options, subprojects: [] }),
      "Sous-projet",
      "provision_subproject_id",
      "Tâche de la provision",
    ],
    [
      "categories",
      (options: ProvisionOptions): ProvisionOptions => ({ ...options, categories: [] }),
      "Catégorie",
      "provision_cost_category_id",
      "Tâche de la provision",
    ],
  ] satisfies [string, (options: ProvisionOptions) => ProvisionOptions, string, string, string][])(
    "opens the form without the field of the %s the session may not read, and sends it without that field",
    async (_name, refuse, absent, key, present) => {
      const client = serve();
      render(modify(CREATED, refuse(OPTIONS)));
      await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
      const form = screen.getByRole("dialog");
      expect(within(form).queryByRole("combobox", { name: absent })).toBeNull();
      expect(within(form).getByRole("combobox", { name: present })).toBeInTheDocument();
      await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
      await vi.waitFor(() => {
        expect(client.calls).toHaveLength(1);
      });
      expect(written(client)).not.toHaveProperty(key);
    },
  );

  it("tells the refusal of the server to the provision of a risk it finds frozen under the form, which stays open with its entry", async () => {
    const client = serve({
      [UPDATE]: { problem: example("risk_provision_frozen") as Problem & { status: 409 } },
    });
    render(modify());
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const form = screen.getByRole("dialog");
    await userEvent.selectOptions(within(form).getByRole("combobox", { name: "Catégorie" }), [
      CONTRACTUAL.id,
    ]);
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent(
      /Condition non remplie\s: risque identifié\./,
    );
    expect(client.calls).toHaveLength(1);
    expect(within(form).getByRole("combobox", { name: "Catégorie" })).toHaveValue(CONTRACTUAL.id);
    expect(announced()).not.toContain("Risque « Indisponibilité de la grue de levage » modifié.");
  });

  it("says the bound of the probability at its field in percentages, the server naming it in the ratio", async () => {
    serve({
      [UPDATE]: {
        problem: example("risk_update_probability_out_of_range") as Problem & { status: 422 },
      },
    });
    render(modify());
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    const form = screen.getByRole("dialog");
    const probability = within(form).getByRole("textbox", { name: "Probabilité (%)" });
    await userEvent.clear(probability);
    await userEvent.type(probability, "120");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(probability).toHaveAccessibleDescription(/100/);
    });
    expect(probability).not.toHaveAccessibleDescription(/\b1\b/);
    expect(probability).toHaveFocus();
    expect(screen.getByRole("dialog")).toBeVisible();
  });

  it.each([
    [
      "tells the risk modified once answered, and keeps the answer in the detail",
      "success",
      /Risque « Indisponibilité de la grue de levage » modifié\./,
    ],
    [
      "tells the service out of reach once the action is rejected",
      "rejected",
      /Le service est injoignable/,
    ],
    [
      "tells the condition the server finds unmet once it refuses",
      "refused",
      /Condition non remplie\s: risque identifié\./,
    ],
  ] satisfies [string, "success" | "rejected" | "refused", RegExp][])(
    "keeps the modification waiting while a write of the dialog closed is under way, %s, then frees it (défaut n° 24)",
    async (_name, kind, said) => {
      const { timing, until, release } = held();
      if (kind === "rejected") {
        failing.until = until;
      }
      const client = serve(
        kind === "refused"
          ? { [UPDATE]: { problem: example("risk_provision_frozen") as Problem & { status: 409 } } }
          : {},
        timing,
      );
      render(modify());
      const command = () => screen.getByRole("button", { name: "Modifier" });
      await userEvent.click(command());
      const form = screen.getByRole("dialog");
      await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
      if (kind !== "rejected") {
        await vi.waitFor(() => {
          expect(client.calls).toHaveLength(1);
        });
      }
      await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
      await vi.waitFor(() => {
        expect(screen.queryByRole("dialog")).toBeNull();
      });
      expect(command()).toHaveAttribute("aria-disabled", "true");
      expect(command()).toHaveAccessibleDescription("Enregistrement en cours…");
      release();
      expect(await screen.findByText(said)).toBeInTheDocument();
      // The user closed the form: the answer does not open it again.
      expect(screen.queryByRole("dialog")).toBeNull();
      await vi.waitFor(() => {
        expect(command()).not.toHaveAttribute("aria-disabled");
      });
      // The service is back: the write the rejected action never made reaches the fake back.
      failing.until = undefined;
      await userEvent.click(command());
      const reopened = screen.getByRole("dialog");
      await userEvent.click(within(reopened).getByRole("button", { name: "Enregistrer" }));
      await vi.waitFor(() => {
        expect(client.calls).toHaveLength(kind === "rejected" ? 1 : 2);
      });
      // Written from the version the answer brought; from the version read when none came.
      const version = kind === "success" ? UPDATED.lock_version : CREATED.lock_version;
      expect(client.calls.at(-1)?.body).toMatchObject({ lock_version: version });
    },
  );

  it("keeps the modification of a risk waiting while its write is under way, though the detail went to another risk and came back, then writes from the version answered (défaut n° 24)", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    const { rerender } = render(detail(CREATED));
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
    rerender(detail(OTHER));
    // The other risk has no write under way.
    expect(command()).not.toHaveAttribute("aria-disabled");
    rerender(detail(CREATED));
    expect(command()).toHaveAttribute("aria-disabled", "true");
    expect(command()).toHaveAccessibleDescription("Enregistrement en cours…");
    await userEvent.click(command());
    expect(screen.queryByRole("dialog")).toBeNull();
    release();
    await vi.waitFor(() => {
      expect(command()).not.toHaveAttribute("aria-disabled");
    });
    // The page has not been read anew: the risk is still the one read, the write goes from the answer.
    await userEvent.click(command());
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Enregistrer" }),
    );
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.body).toMatchObject({ lock_version: UPDATED.lock_version });
  });

  it.each([
    ["success", /modifié\./],
    ["rejected", /Le service est injoignable/],
    ["refused", /Condition non remplie/],
  ] satisfies [string, RegExp][])(
    "tells nothing on the risk the detail went to while a write of the previous one is under way, once it is answered: %s (défaut n° 1)",
    async (kind, said) => {
      const { timing, until, release } = held();
      if (kind === "rejected") {
        failing.until = until;
      }
      const client = serve(
        kind === "refused"
          ? { [UPDATE]: { problem: example("risk_provision_frozen") as Problem & { status: 409 } } }
          : {},
        timing,
      );
      const { rerender } = render(detail(CREATED));
      await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
      await userEvent.click(
        within(screen.getByRole("dialog")).getByRole("button", { name: "Enregistrer" }),
      );
      if (kind !== "rejected") {
        await vi.waitFor(() => {
          expect(client.calls).toHaveLength(1);
        });
      }
      rerender(detail(OTHER));
      expect(screen.queryByRole("dialog")).toBeNull();
      release();
      // The answer is awaited where it would have been told, then nothing of it is found.
      await new Promise((resolve) => setTimeout(resolve, 100));
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(screen.queryByText(said)).toBeNull();
      expect(announced().every((status) => status === "" || status === null)).toBe(true);
      const command = screen.getByRole("button", { name: "Modifier" });
      expect(command).not.toHaveAttribute("aria-disabled");
      expect(command).not.toHaveAttribute("aria-busy", "true");
    },
  );
});
