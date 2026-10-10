// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  type Problem,
} from "@/test/fixtures";

import { IndicatorSettings, RiskSettings } from "./settings-forms";

type ReferenceSettings = components["schemas"]["ReferenceSettings"];

// The server of Next, as far as the forms need it: the fake back, and the page rendered again once
// the settings are written.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// A write whose server action rejects once `until` settles — the API out of reach, as `fetch`
// rejects in the browser —; none, and the action asks the fake back.
const failing = vi.hoisted((): { until: Promise<void> | undefined } => ({ until: undefined }));
vi.mock("@/api/actions/reference", async (original) => {
  const actual = await original<typeof import("@/api/actions/reference")>();
  return {
    ...actual,
    updateReferenceSettings: async (
      ...asked: Parameters<typeof actual.updateReferenceSettings>
    ) => {
      if (failing.until === undefined) {
        return actual.updateReferenceSettings(...asked);
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
  usePathname: () => "/reference/risks",
  useSearchParams: () => new URLSearchParams(),
}));

const UPDATE = "PATCH /reference/settings";
const witness = example("reference_settings") as ReferenceSettings;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(answers, timing);
  server.client = client;
  return client;
}

/** A part of the screen, in French. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

/** Open the form of the risk matrix, and give it back. */
async function openRisks(): Promise<HTMLElement> {
  render(inFrench(<RiskSettings settings={witness} />));
  await userEvent.click(screen.getByRole("button", { name: "Modifier la matrice de risques" }));
  return screen.getByRole("dialog", { name: "Modifier la matrice de risques" });
}

/** Open the form of the thresholds and the delay, and give it back. */
async function openIndicators(): Promise<HTMLElement> {
  render(inFrench(<IndicatorSettings settings={witness} />));
  await userEvent.click(screen.getByRole("button", { name: "Modifier les seuils et le délai" }));
  return screen.getByRole("dialog", { name: "Modifier les seuils et le délai" });
}

/**
 * A field of a form, by its name: the legend of its group, then its label — the label alone repeats
 * from one group to the next.
 */
function field(
  form: HTMLElement,
  group: string,
  label: string,
  role: "textbox" | "combobox" = "textbox",
): HTMLElement {
  return within(form).getByRole(role, { name: `${group} ${label}` });
}

/** Put a text in place of what a field holds. */
async function retype(control: HTMLElement, text: string) {
  await userEvent.clear(control);
  await userEvent.type(control, text);
}

/** What the region of the settings says, among the regions of the screen that say nothing. */
function said(): HTMLElement | undefined {
  return screen.getAllByRole("status").find((region) => region.textContent !== "");
}

/** Send a form. */
async function save(form: HTMLElement) {
  await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
}

const PROBABILITY = "Bornes de probabilité (%)";
const SEVERITY = "Bornes de gravité (% du budget de référence)";
const COST = "Indice de coût";
const SCHEDULE = "Indice de délai";

afterEach(() => {
  failing.until = undefined;
  refresh.mockClear();
  router.refresh.mockClear();
});

describe("the form of the risk matrix", () => {
  it("modifies the six bounds and the zones, sends the matrix alone with the version read, and shows the answer in place of the reading [WF-REF-0160-A]", async () => {
    // Les six bornes sont saisissables et ordonnées.
    const client = serve({ [UPDATE]: "reference_settings_matrix_updated" });
    const form = await openRisks();
    // Entered as percentages, as the table shows them.
    expect(field(form, PROBABILITY, "Deuxième borne")).toHaveValue("30");
    await retype(field(form, PROBABILITY, "Deuxième borne"), "25");
    await retype(field(form, PROBABILITY, "Troisième borne"), "50");
    await retype(field(form, SEVERITY, "Première borne"), "2");
    // The cell of the lowest probability and the highest severity, the fourth zone of the contract.
    const corner = field(form, "Probabilité, niveau 1", "Gravité, niveau 4", "combobox");
    expect(corner).toHaveValue("watch");
    await userEvent.selectOptions(corner, "Alerte");
    await save(form);
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // The matrix alone, never the thresholds, the delay, the currency nor the language.
    expect(client.calls.map(({ route, body }) => ({ route, body }))).toEqual([
      {
        route: UPDATE,
        body: {
          risk_matrix: {
            probability_bounds: ["0.1", "0.25", "0.5"],
            severity_bounds: ["0.02", "0.05", "0.1"],
            zones: witness.risk_matrix.zones.with(3, "alert"),
          },
          lock_version: 1,
        },
      },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(said()).toHaveTextContent("Matrice de risques enregistrée.");
    const bounds = screen.getByRole("table", { name: "Bornes de la matrice de risques" });
    const row = (axis: string) =>
      within(bounds).getByRole("rowheader", { name: axis }).closest("tr");
    expect(row("Probabilité")).toHaveTextContent("Probabilité10 %25 %50 %");
    expect(row("Gravité, en pourcentage du budget de référence")).toHaveTextContent(
      "Gravité, en pourcentage du budget de référence2 %5 %10 %",
    );
    expect(screen.getByRole("button", { name: "Modifier la matrice de risques" })).toHaveFocus();
  });

  it("refuses before asking anything each bound that is not strictly above the one before it, the first taking the focus [WF-REF-0160-A]", async () => {
    const client = serve({ [UPDATE]: "reference_settings_matrix_updated" });
    const form = await openRisks();
    await retype(field(form, PROBABILITY, "Deuxième borne"), "5");
    await retype(field(form, SEVERITY, "Troisième borne"), "5");
    await save(form);
    const below = field(form, PROBABILITY, "Deuxième borne");
    const equal = field(form, SEVERITY, "Troisième borne");
    for (const bound of [below, equal]) {
      expect(bound).toHaveAttribute("aria-invalid", "true");
      expect(bound).toHaveAccessibleDescription("Les bornes doivent être strictement croissantes.");
    }
    expect(below).toHaveFocus();
    // The bound before it breaks no order: it is not refused.
    expect(field(form, PROBABILITY, "Première borne")).not.toHaveAttribute("aria-invalid");
    expect(client.calls).toEqual([]);
  });

  it("says at its field the bound the server refuses, the form open to correct it", async () => {
    serve({
      [UPDATE]: {
        problem: example("reference_settings_bounds_refused") as Problem & { status: 422 },
      },
    });
    const form = await openRisks();
    await save(form);
    const second = field(form, SEVERITY, "Deuxième borne");
    await vi.waitFor(() => {
      expect(second).toHaveFocus();
    });
    expect(second).toHaveAccessibleDescription("Les bornes doivent être strictement croissantes.");
    expect(within(form).queryByRole("alert")).toBeNull();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("tells under the form the permission the session lacks, which the server names", async () => {
    serve({
      [UPDATE]: {
        problem: example("reference_settings_permission_missing") as Problem & { status: 403 },
      },
    });
    const form = await openRisks();
    await save(form);
    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire. Permission requise : Modifier les paramètres de risques.",
    );
  });

  it("names each of its fields, its zones gathered by level of probability", async () => {
    serve({});
    const form = await openRisks();
    expect(within(form).getAllByRole("group")).toHaveLength(6);
    expect(within(form).getAllByRole("combobox")).toHaveLength(16);
    // Each named after its group first, its label alone repeated from one group to the next.
    expect(within(form).getAllByRole("combobox", { name: /Gravité, niveau 4$/ })).toHaveLength(4);
    await expectAccessible(form);
  });

  it("keeps its command inactive while a write of the dialog closed is under way, shows its answer, then opens on the version it brings (#661)", async () => {
    const settles: (() => void)[] = [];
    const until = new Promise<void>((settle) => {
      settles.push(settle);
    });
    const client = serve({ [UPDATE]: "reference_settings_matrix_updated" }, { hold: () => until });
    const form = await openRisks();
    await save(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    // Opened anew now, the form would write from the version its own answer is about to replace.
    const command = screen.getByRole("button", { name: "Modifier la matrice de risques" });
    // The focus back on the command, which says why it waits.
    expect(command).toHaveFocus();
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAttribute("aria-busy", "true");
    expect(command).toHaveAccessibleDescription("Enregistrement en cours…");
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
    for (const settle of settles) {
      settle();
    }
    await vi.waitFor(() => {
      expect(said()).toHaveTextContent("Matrice de risques enregistrée.");
    });
    const bounds = screen.getByRole("table", { name: "Bornes de la matrice de risques" });
    expect(
      within(bounds).getByRole("rowheader", { name: "Probabilité" }).closest("tr"),
    ).toHaveTextContent("Probabilité10 %25 %50 %");
    expect(command).not.toHaveAttribute("aria-disabled");
    await userEvent.click(command);
    await save(screen.getByRole("dialog", { name: "Modifier la matrice de risques" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.body).toMatchObject({
      risk_matrix: { probability_bounds: ["0.1", "0.25", "0.5"] },
      lock_version: 2,
    });
  });
});

describe("the form of the thresholds and the delay", () => {
  it("modifies the four thresholds and the delay, sends them alone with the version read, and shows the answer [WF-REF-0170-A] [WF-REF-0180-A]", async () => {
    // Les quatre seuils sont saisissables ; le délai est saisissable en semaines.
    const client = serve({ [UPDATE]: "reference_settings_thresholds_updated" });
    const form = await openIndicators();
    expect(field(form, COST, "Seuil de vigilance")).toHaveValue("0,9");
    for (const group of [COST, SCHEDULE]) {
      await retype(field(form, group, "Seuil de vigilance"), "0,95");
      await retype(field(form, group, "Seuil d’alerte"), "0,85");
    }
    const weeks = within(form).getByLabelText(
      "Délai maximal entre deux révisions marquées (semaines)",
    );
    expect(weeks).toHaveValue("8");
    await retype(weeks, "6");
    await save(form);
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(client.calls.map(({ body }) => body)).toEqual([
      {
        index_thresholds: {
          cost_watch: "0.95",
          cost_alert: "0.85",
          schedule_watch: "0.95",
          schedule_alert: "0.85",
        },
        max_weeks_between_reviews: 6,
        lock_version: 1,
      },
    ]);
    expect(said()).toHaveTextContent("Seuils et délai enregistrés.");
    expect(screen.getByRole("table", { name: "Seuils d’alerte des indices" })).toHaveTextContent(
      "Indice de coût0,950,85",
    );
    expect(screen.getByText(/6 semaines/)).toBeInTheDocument();
  });

  it("refuses before asking anything an alert threshold that is not below its watch threshold, the first taking the focus [WF-REF-0170-A]", async () => {
    const client = serve({ [UPDATE]: "reference_settings_thresholds_updated" });
    const form = await openIndicators();
    await retype(field(form, COST, "Seuil d’alerte"), "0,9");
    await retype(field(form, SCHEDULE, "Seuil d’alerte"), "0,95");
    await save(form);
    for (const group of [COST, SCHEDULE]) {
      expect(field(form, group, "Seuil d’alerte")).toHaveAccessibleDescription(
        "Le seuil d’alerte doit être inférieur au seuil de vigilance.",
      );
    }
    expect(field(form, COST, "Seuil d’alerte")).toHaveFocus();
    expect(client.calls).toEqual([]);
  });

  it("refuses at its field, before asking anything, a delay that is no whole number of weeks [WF-REF-0180-A]", async () => {
    // Le délai est saisissable en semaines : entières, comme le contrat les compte.
    const client = serve({ [UPDATE]: "reference_settings_thresholds_updated" });
    const form = await openIndicators();
    const weeks = within(form).getByRole("textbox", {
      name: "Délai maximal entre deux révisions marquées (semaines)",
    });
    await retype(weeks, "8,5");
    await save(form);
    expect(weeks).toHaveAttribute("aria-invalid", "true");
    expect(weeks).toHaveAccessibleDescription("Le délai est un nombre entier de semaines.");
    expect(weeks).toHaveFocus();
    expect(client.calls).toEqual([]);
  });

  it("says at its field each alert threshold the server refuses", async () => {
    serve({
      [UPDATE]: {
        problem: example("reference_settings_thresholds_refused") as Problem & { status: 422 },
      },
    });
    const form = await openIndicators();
    await save(form);
    await vi.waitFor(() => {
      expect(field(form, COST, "Seuil d’alerte")).toHaveFocus();
    });
    expect(field(form, SCHEDULE, "Seuil d’alerte")).toHaveAttribute("aria-invalid", "true");
    expect(within(form).queryByRole("alert")).toBeNull();
  });

  it("says the version stale under the form, which another screen wrote, and offers to read the page anew", async () => {
    serve({
      [UPDATE]: { problem: example("reference_settings_stale") as Problem & { status: 412 } },
    });
    const form = await openIndicators();
    await save(form);
    await userEvent.click(await within(form).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("tells above the settings a refusal answered once the dialog is gone, and frees its command", async () => {
    const settles: (() => void)[] = [];
    const until = new Promise<void>((settle) => {
      settles.push(settle);
    });
    serve(
      {
        [UPDATE]: {
          problem: example("reference_settings_thresholds_refused") as Problem & { status: 422 },
        },
      },
      { hold: () => until },
    );
    const form = await openIndicators();
    await save(form);
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    const command = screen.getByRole("button", { name: "Modifier les seuils et le délai" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    for (const settle of settles) {
      settle();
    }
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Les données saisies ne sont pas valides.",
    );
    expect(command).not.toHaveAttribute("aria-disabled");
    await userEvent.click(command);
    expect(screen.getByRole("dialog", { name: "Modifier les seuils et le délai" })).toBeVisible();
  });

  it("frees its command once a write of the dialog closed is rejected, the API out of reach, and says so", async () => {
    const settles: (() => void)[] = [];
    failing.until = new Promise<void>((settle) => {
      settles.push(settle);
    });
    serve({ [UPDATE]: "reference_settings_thresholds_updated" });
    const form = await openIndicators();
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    const command = screen.getByRole("button", { name: "Modifier les seuils et le délai" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    for (const settle of settles) {
      settle();
    }
    expect(await screen.findByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(command).not.toHaveAttribute("aria-disabled");
    await userEvent.click(command);
    expect(screen.getByRole("dialog", { name: "Modifier les seuils et le délai" })).toBeVisible();
  });

  it("keeps the answer through a reading anew of the version it answered, and gives way to a newer reading, which the form writes from (défaut n° 22)", async () => {
    const client = serve({ [UPDATE]: "reference_settings_thresholds_updated" });
    const { rerender } = render(inFrench(<IndicatorSettings settings={witness} />));
    const open = () =>
      userEvent.click(screen.getByRole("button", { name: "Modifier les seuils et le délai" }));
    await open();
    await save(screen.getByRole("dialog"));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // The page read anew serves the version 1 again — the fake back keeps nothing: the answer stays.
    rerender(inFrench(<IndicatorSettings settings={witness} />));
    expect(screen.getByText(/6 semaines/)).toBeInTheDocument();
    // A reading newer than the answer prevails — the matrix written meanwhile by the other screen,
    // then the delay —, and the form writes from it.
    const newer = { ...witness, max_weeks_between_reviews: 4, lock_version: 3 };
    rerender(inFrench(<IndicatorSettings settings={newer} />));
    expect(screen.getByText(/4 semaines/)).toBeInTheDocument();
    await open();
    await save(screen.getByRole("dialog"));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.body).toMatchObject({ max_weeks_between_reviews: 4, lock_version: 3 });
  });
});
