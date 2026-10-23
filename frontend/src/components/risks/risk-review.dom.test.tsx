// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  held,
  type Problem,
} from "@/test/fixtures";

import type { ProvisionOptions } from "./provision-choices";
import { type Risk, type RiskReview, RiskDetail } from "./risk-detail";

// The server of Next, as far as the review needs it: the fake back, and the page read anew once a
// write is answered.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/r/risks",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVIEW = "POST /projects/{project_id}/risks/{risk_id}/reviews";
const UPDATE = "PATCH /projects/{project_id}/risks/{risk_id}";

const IDENTIFIED = example("risk") as Risk;
const REVIEWED = example("risk_reviewed") as Risk;
const OCCURRED = example("risk_occurred_detail") as Risk;
const REVIEWS = example("risk_reviews") as RiskReview[];
const REVIEWS_AFTER = example("risk_reviews_reviewed") as RiskReview[];
// The risk dismissed of the register, whose category of provision is active.
const AUTOMATION: Risk = (() => {
  const found = (example("risks") as { items: Risk[] }).items.find(
    ({ state }) => state === "dismissed",
  );
  if (found === undefined) {
    throw new Error("the contract lists no risk dismissed");
  }
  return found;
})();
// A counterfactual: its category deactivated since it was dismissed, which no example of the
// contract shows — the contract has no risk dismissed under a category deactivated.
const DEACTIVATED: Risk = {
  ...AUTOMATION,
  provision_cost_category_is_active: false,
  provision_cost_category_label: "Provisions pour risques",
};

const ONE = { id: "01926f3a-7c00-7000-8000-000000000404", label: "Provisions pour risques" };
const CONTRACTUAL = { id: "01926f3a-7c00-7000-8000-000000000405", label: "Aléas contractuels" };
const OPTIONS: ProvisionOptions = { categories: [ONE, CONTRACTUAL], subprojects: [], tasks: [] };

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing = {}): FakeClient {
  const client = fakeClient(
    { [REVIEW]: { example: "risk_reviewed", status: 201 }, ...answers },
    timing,
  );
  server.client = client;
  return client;
}

/** The detail of a risk, in French, as the screen of the risks hands it. */
function detail(
  risk: Risk,
  reviews: readonly RiskReview[] = REVIEWS,
  options: ProvisionOptions = OPTIONS,
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <RiskDetail risk={risk} reviews={reviews} projectId={PROJECT} options={options} />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The command that reviews the risk. */
function command(): HTMLElement {
  return screen.getByRole("button", { name: "Réexaminer" });
}

/** The form of the review, once opened. */
async function open(): Promise<HTMLElement> {
  await userEvent.click(command());
  return screen.getByRole("dialog");
}

/** Send the form of the review. */
async function send(form: HTMLElement) {
  await userEvent.click(within(form).getByRole("button", { name: "Réexaminer" }));
}

beforeEach(() => {
  sessionStorage.clear();
  forgetMessages();
});

afterEach(() => {
  vi.restoreAllMocks();
  refresh.mockClear();
  router.push.mockClear();
});

describe("« Réexaminer » a risk", () => {
  it("confirms a risk with no change, and the history of its reviews shows the review dated [WF-RIS-0010-A]", async () => {
    const client = serve();
    const { rerender } = render(detail(IDENTIFIED));
    const before = screen.getByRole("table", { name: "Historique des réexamens" });
    expect(within(before).getAllByRole("row")).toHaveLength(REVIEWS.length + 1);
    const form = await open();
    // The form starts from what the risk holds: a confirmation is one press away.
    expect(within(form).getByRole("textbox", { name: "Probabilité (%)" })).toHaveValue("40");
    expect(within(form).getByRole("combobox", { name: "État retenu" })).toHaveValue("identified");
    await send(form);
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(client.calls).toHaveLength(1);
    expect(client.calls[0]?.route).toBe(REVIEW);
    expect(client.calls[0]?.path).toBe(`/projects/${PROJECT}/risks/${IDENTIFIED.risk_id}/reviews`);
    expect(client.calls[0]?.body).toEqual({
      probability: "0.4",
      state: "identified",
      lock_version: IDENTIFIED.lock_version,
    });
    expect(
      screen
        .getAllByRole("status")
        .some(
          (status) => status.textContent === "Risque « Risque de reprise du câblage » réexaminé.",
        ),
    ).toBe(true);
    expect(refresh).toHaveBeenCalledOnce();
    // The page read anew: the review of the day heads the history, dated.
    rerender(detail(REVIEWED, REVIEWS_AFTER));
    const after = screen.getByRole("table", { name: "Historique des réexamens" });
    const rows = within(after).getAllByRole("row");
    expect(rows).toHaveLength(REVIEWS_AFTER.length + 1);
    expect(rows[1]).toHaveTextContent(/03\/06\/2026/);
    expect(rows[1]).toHaveTextContent("40 %");
    expect(rows[1]).toHaveTextContent("Identifié");
  });

  it("dismisses an identified risk, and brings a dismissed risk back to identified [WF-RIS-0020-A]", async () => {
    const client = serve({ [REVIEW]: { example: "risk_dismissed", status: 201 } });
    const { rerender } = render(detail(IDENTIFIED));
    let form = await open();
    await userEvent.selectOptions(within(form).getByRole("combobox", { name: "État retenu" }), [
      "dismissed",
    ]);
    await send(form);
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(client.calls[0]?.body).toMatchObject({ state: "dismissed", probability: "0.4" });
    // The commands follow the risk the answer brings: dismissed, it is no longer declared occurred.
    expect(screen.getByRole("button", { name: "Déclarer survenu" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    // A risk dismissed, the way back: the automation engineer, identified again at 5 %.
    server.client = fakeClient({ [REVIEW]: { example: "risk_reidentified", status: 201 } });
    rerender(detail(AUTOMATION));
    form = await open();
    expect(within(form).getByRole("combobox", { name: "État retenu" })).toHaveValue("dismissed");
    // Its category is still active: it is not asked again.
    expect(within(form).queryByRole("combobox", { name: "Catégorie" })).toBeNull();
    await userEvent.selectOptions(within(form).getByRole("combobox", { name: "État retenu" }), [
      "identified",
    ]);
    await send(form);
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    const calls = (server.client as FakeClient).calls;
    expect(calls[0]?.body).toEqual({
      probability: "0.05",
      state: "identified",
      lock_version: AUTOMATION.lock_version,
    });
  });

  it("offers no review of a risk occurred, from which no transition goes [WF-RIS-0020-A]", () => {
    render(detail(OCCURRED, []));
    expect(command()).toHaveAttribute("aria-disabled", "true");
    expect(command()).toHaveAccessibleDescription(
      /^Condition non remplie\s: risque non survenu\.$/,
    );
  });

  it("tells the refusal of a review of a risk occurred under the form, which stays open [WF-RIS-0020-A]", async () => {
    serve({
      [REVIEW]: { problem: example("risk_review_occurred") as Problem & { status: 409 } },
    });
    render(detail(IDENTIFIED));
    const form = await open();
    await send(form);
    const refusal = await within(form).findByRole("alert");
    expect(refusal).toHaveTextContent(/risque non survenu/);
    expect(screen.getByRole("dialog")).toBe(form);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the bound of the probability at its field in percentages, the server naming it in the ratio", async () => {
    serve({
      [REVIEW]: {
        problem: example("risk_review_probability_out_of_range") as Problem & { status: 422 },
      },
    });
    render(detail(IDENTIFIED));
    const form = await open();
    const probability = within(form).getByRole("textbox", { name: "Probabilité (%)" });
    await userEvent.clear(probability);
    await userEvent.type(probability, "120");
    await send(form);
    await vi.waitFor(() => {
      expect(probability).toHaveAccessibleDescription(/100/);
    });
    expect(probability).not.toHaveAccessibleDescription(/\b1\b/);
    expect(probability).toHaveFocus();
  });

  it("asks another category of a risk dismissed whose own is deactivated, only for its return, among the active ones", async () => {
    const client = serve({ [REVIEW]: { example: "risk_reidentified", status: 201 } });
    render(detail(DEACTIVATED));
    const form = await open();
    const category = within(form).getByRole("combobox", { name: "Catégorie" });
    expect(
      within(category)
        .getAllByRole("option")
        .map((each) => each.textContent),
    ).toEqual(["Choisir…", ONE.label, CONTRACTUAL.label]);
    // Kept dismissed, nothing is asked of the category, and none is sent.
    await send(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).not.toHaveProperty("provision_cost_category_id");
  });

  it("requires the category to bring such a risk back to identified, and sends the one chosen", async () => {
    const client = serve({ [REVIEW]: { example: "risk_reidentified", status: 201 } });
    render(detail(DEACTIVATED));
    const form = await open();
    await userEvent.selectOptions(within(form).getByRole("combobox", { name: "État retenu" }), [
      "identified",
    ]);
    await send(form);
    const category = within(form).getByRole("combobox", { name: "Catégorie" });
    expect(category).toHaveAttribute("aria-invalid", "true");
    expect(category).toHaveFocus();
    expect(client.calls).toHaveLength(0);
    await userEvent.selectOptions(category, [CONTRACTUAL.id]);
    await send(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toMatchObject({
      state: "identified",
      provision_cost_category_id: CONTRACTUAL.id,
    });
  });

  it("does not ask the category when the return has one alone to choose", async () => {
    serve();
    render(detail(DEACTIVATED, REVIEWS, { ...OPTIONS, categories: [ONE] }));
    const form = await open();
    expect(within(form).queryByRole("combobox", { name: "Catégorie" })).toBeNull();
  });

  it("keeps the modification waiting while a review is under way, then writes from the version the review brought (défaut n° 24)", async () => {
    const { timing, release } = held();
    const client = serve({ [UPDATE]: "risk_updated" }, timing);
    render(detail(IDENTIFIED));
    const form = await open();
    await send(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    const modify = screen.getByRole("button", { name: "Modifier" });
    expect(modify).toHaveAttribute("aria-disabled", "true");
    expect(command()).toHaveAttribute("aria-disabled", "true");
    release();
    await vi.waitFor(() => {
      expect(modify).not.toHaveAttribute("aria-disabled");
    });
    await userEvent.click(modify);
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Enregistrer" }),
    );
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.route).toBe(UPDATE);
    expect(client.calls[1]?.body).toMatchObject({ lock_version: REVIEWED.lock_version });
  });
});
