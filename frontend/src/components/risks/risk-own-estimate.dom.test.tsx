// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { type Risk, RiskDetail } from "./risk-detail";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/r/risks",
  useSearchParams: () => new URLSearchParams(),
}));

type Condition = components["schemas"]["CommandCondition"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000002";
const STRUCTURE = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}";
const REPORT = `GET ${STRUCTURE}/rebase` as const;
const REBASE = `POST ${STRUCTURE}/rebase` as const;
const RECOMPOSE = `POST ${STRUCTURE}/recompose` as const;
const READ_RISK = "GET /projects/{project_id}/risks/{risk_id}";
const REVIEW = "POST /projects/{project_id}/risks/{risk_id}/reviews";
const OCCURRENCE_REPORT = "GET /projects/{project_id}/risks/{risk_id}/occurrence";

const IDENTIFIED = example("risk") as Risk;

/** The risk as the page lists it, `review` and `declare_occurrence` lacking what is given. */
function lacking(missing: readonly Condition[], lockVersion = IDENTIFIED.lock_version - 1): Risk {
  return {
    ...IDENTIFIED,
    lock_version: lockVersion,
    available_commands: IDENTIFIED.available_commands.map((offer) =>
      offer.command === "review" || offer.command === "declare_occurrence"
        ? { ...offer, is_available: false, missing_conditions: [...missing] }
        : offer,
    ),
  };
}

const LATE = lacking(["own_estimate_up_to_date"]);

function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

function detail(risk: Risk) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <RiskDetail
          risk={risk}
          reviews={[]}
          projectId={PROJECT}
          revisionId={REVISION}
          options={undefined}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

const CLEAN: FakeAnswers = {
  [REPORT]: { example: "structure_rebase_report_risk_clean", status: 200 },
  [REBASE]: { example: "structure_rebased_risk", status: 200 },
  [READ_RISK]: { example: "risk", status: 200 },
};

beforeEach(() => {
  sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  vi.restoreAllMocks();
  router.refresh.mockReset();
});

describe("« Réexaminer » devant un devis propre en retard [US-3140] [WF-RIS-0070-A]", () => {
  it("met à jour sans rien demander quand le compte rendu ne signale rien, puis présente la gravité recalculée et réexamine depuis le risque relu", async () => {
    const client = serve({ ...CLEAN, [REVIEW]: { example: "risk_reviewed", status: 201 } });
    render(detail(LATE));
    await userEvent.click(screen.getByRole("button", { name: "Réexaminer" }));
    const form = await screen.findByRole("dialog");
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, READ_RISK]);
    expect(form).toHaveTextContent(/gravité recalculée est de 1\s250\s000,00/);
    await userEvent.click(within(form).getByRole("button", { name: "Réexaminer" }));
    await vi.waitFor(() => {
      expect(client.calls.at(-1)?.route).toBe(REVIEW);
    });
    expect(client.calls.at(-1)?.body).toMatchObject({ lock_version: IDENTIFIED.lock_version });
  });

  it("présente à confirmer une mise à jour qui garde une valeur, avec la gravité recalculée, sans rien écrire avant la confirmation", async () => {
    const client = serve({
      ...CLEAN,
      [REPORT]: { example: "structure_rebase_report_risk", status: 200 },
    });
    render(detail(LATE));
    await userEvent.click(screen.getByRole("button", { name: "Réexaminer" }));
    const step = await screen.findByRole("region", { name: "Mise à jour du devis propre" });
    expect(step).toHaveTextContent(/garde une valeur contre le projet/);
    expect(step).toHaveTextContent(/Gravité recalculée : 1\s249\s880,00/);
    expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
    await userEvent.click(
      within(step).getByRole("button", { name: "Confirmer la mise à jour du devis propre" }),
    );
    await screen.findByRole("dialog");
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, READ_RISK]);
  });

  it("dit ce qui est à corriger d'une mise à jour refusée, sans offrir de la confirmer", async () => {
    const client = serve({
      ...CLEAN,
      [REPORT]: { example: "structure_rebase_report_risk_refused", status: 200 },
    });
    render(detail(LATE));
    await userEvent.click(screen.getByRole("button", { name: "Réexaminer" }));
    const step = await screen.findByRole("region", { name: "Mise à jour du devis propre" });
    expect(step).toHaveTextContent(/est refusée : corrigez le devis propre/);
    expect(within(step).getByRole("alert")).toBeVisible();
    expect(within(step).queryByRole("button", { name: /Confirmer/ })).toBeNull();
    expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
  });

  it("laisse écarter le risque sans mise à jour : le réexamen qui écarte n'en demande pas", async () => {
    const client = serve({
      ...CLEAN,
      [REPORT]: { example: "structure_rebase_report_risk_refused", status: 200 },
      [REVIEW]: { example: "risk_reviewed", status: 201 },
    });
    render(detail(LATE));
    await userEvent.click(screen.getByRole("button", { name: "Réexaminer" }));
    const step = await screen.findByRole("region", { name: "Mise à jour du devis propre" });
    await userEvent.click(
      within(step).getByRole("button", { name: "Écarter le risque sans mise à jour" }),
    );
    const form = await screen.findByRole("dialog");
    expect(within(form).getByRole("combobox", { name: /État retenu/ })).toHaveValue("dismissed");
    await userEvent.click(within(form).getByRole("button", { name: "Réexaminer" }));
    await vi.waitFor(() => {
      expect(client.calls.at(-1)?.route).toBe(REVIEW);
    });
    expect(client.calls.some((call) => call.route === REBASE)).toBe(false);
    expect(client.calls.at(-1)?.body).toMatchObject({
      state: "dismissed",
      lock_version: LATE.lock_version,
    });
  });

  it("recompose d'abord un devis propre élagué, puis le met à jour", async () => {
    const client = serve({
      ...CLEAN,
      [RECOMPOSE]: { example: "structure_recomposed_late", status: 200 },
    });
    render(detail(lacking(["own_estimate_whole", "own_estimate_up_to_date"])));
    await userEvent.click(screen.getByRole("button", { name: "Réexaminer" }));
    await screen.findByRole("dialog");
    expect(client.calls.map((call) => call.route)).toEqual([RECOMPOSE, REPORT, REBASE, READ_RISK]);
  });

  it("n'enchaîne rien quand la commande manque d'autre chose que du devis propre", async () => {
    const client = serve(CLEAN);
    render(detail(lacking(["risk_not_occurred", "own_estimate_up_to_date"])));
    const command = screen.getByRole("button", { name: "Réexaminer" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(command);
    expect(client.calls).toHaveLength(0);
  });
});

describe("« Déclarer survenu » devant un devis propre en retard [US-3140] [WF-RIS-0070-A]", () => {
  it("met à jour le devis propre sans rien demander, puis présente le compte rendu de la survenance", async () => {
    const client = serve({
      ...CLEAN,
      [OCCURRENCE_REPORT]: { example: "risk_occurrence_report_abandoned_task", status: 200 },
    });
    render(detail(LATE));
    await userEvent.click(screen.getByRole("button", { name: "Déclarer survenu" }));
    const form = await screen.findByRole("form", { name: "Déclarer survenu" });
    expect(await within(form).findByRole("table", { name: /écarts/i })).toBeVisible();
    expect(client.calls.map((call) => call.route)).toEqual([
      REPORT,
      REBASE,
      READ_RISK,
      OCCURRENCE_REPORT,
    ]);
  });

  it("présente à confirmer une mise à jour qui garde une valeur, et ne lit pas le compte rendu de la survenance avant", async () => {
    const client = serve({
      ...CLEAN,
      [REPORT]: { example: "structure_rebase_report_risk", status: 200 },
    });
    render(detail(LATE));
    await userEvent.click(screen.getByRole("button", { name: "Déclarer survenu" }));
    const step = await screen.findByRole("region", { name: "Mise à jour du devis propre" });
    expect(step).toHaveTextContent(/garde une valeur/);
    expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
    expect(screen.queryByRole("form", { name: "Déclarer survenu" })).toBeNull();
  });
});

describe("le détail d'un risque survenu [US-3140] [WF-RIS-0050-A]", () => {
  it("présente son coût à la survenance, signé, et en regard ce qu'il coûte aujourd'hui", () => {
    const occurred: Risk = {
      ...(example("risk_occurred_detail") as Risk),
      occurrence_cost: "-4000.00",
      occurred_reestimated_amount: "1500.00",
    };
    render(detail(occurred));
    const cost = screen.getByText("Coût à la survenance");
    expect(cost.closest("div")).toHaveTextContent(/-\s?4\s000,00/);
    const today = screen.getByText("Ce qu’il coûte aujourd’hui");
    expect(today.closest("div")).toHaveTextContent(/1\s500,00/);
  });

  it("ne présente aucun coût aujourd'hui pour un risque qui n'est pas survenu", () => {
    render(detail(IDENTIFIED));
    expect(screen.queryByText("Ce qu’il coûte aujourd’hui")).toBeNull();
  });
});
