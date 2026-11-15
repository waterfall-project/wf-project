// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the risks and of the indicators, the correspondence of the actual costs and the
 * card of the installation, in the layout of EP-25 (US-2110/L2, US-2120/L2): the command that
 * modifies the risks or the indicators outlined at the right of the title of the screen; the
 * correspondence in a card of the columns read and a card of the columns kept, its fields bounded to
 * a reading width, its save filled at the foot; the name of the company, and its command, in the
 * card of the installation, with the currency, the default language and the time zone read only.
 */
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { expectCommandRule } from "@/test/command-rule";
import { example, fakeClient } from "@/test/fixtures";

import { ActualCostMapping } from "./actual-cost-mapping";
import {
  IndicatorSettings,
  InstallationCard,
  InstallationSettings,
  RiskSettings,
} from "./settings-forms";

type ReferenceSettings = components["schemas"]["ReferenceSettings"];
type Mapping = components["schemas"]["ActualCostMapping"];

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/reference/risks",
  useSearchParams: () => new URLSearchParams(),
}));

const settings = example("reference_settings") as ReferenceSettings;
const mapping = example("actual_cost_mapping") as Mapping;
const installation = example("installation") as components["schemas"]["Installation"];

/** A part of the screen, in French. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

/** Whether a button is drawn filled. */
function filled(button: HTMLElement): boolean {
  return button.classList.contains("bg-primary");
}

afterEach(() => {
  server.client = undefined;
});

describe.each([
  ["risks", "Paramètres de risques", "Modifier la matrice de risques", RiskSettings],
  ["indicators", "Paramètres d’indicateurs", "Modifier les seuils et le délai", IndicatorSettings],
] as const)("the command that modifies the %s", (_name, title, command, Settings) => {
  it("is outlined at the right of the title of the screen, in its header and in no card", async () => {
    server.client = fakeClient({});
    const { container } = render(inFrench(<Settings settings={settings} />));
    const heading = screen.getByRole("heading", { level: 1, name: title });
    const button = screen.getByRole("button", { name: command });
    const commands = button.closest('[data-slot="screen-commands"]');
    expect(commands).not.toBeNull();
    // The header holds the title and the commands, side by side: one row, the title first.
    expect(commands?.parentElement?.contains(heading)).toBe(true);
    expect(filled(button)).toBe(false);
    expect(button).toHaveClass("border", "border-input", "bg-background");
    expect(button.closest('[data-slot="section-card"]')).toBeNull();
    expectCommandRule(container);
    await expectAccessible(container);
  });

  it("opens the form of the screen entire, and gives the focus back to the command on closing [WF-IHM-0100-A]", async () => {
    server.client = fakeClient({});
    render(inFrench(<Settings settings={settings} />));
    const button = screen.getByRole("button", { name: command });
    await userEvent.click(button);
    const form = screen.getByRole("dialog", { name: command });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(button);
  });
});

describe("the card of the installation", () => {
  it("stands in a card, its command outlined at the right of the title, the principal one that modifies, with the three facts the bootstrap fixed read only", async () => {
    server.client = fakeClient({});
    const { container } = render(
      inFrench(<InstallationSettings settings={settings} installation={installation} />),
    );
    const card = screen.getByRole("region", { name: "Installation" });
    const button = within(card).getByRole("button", { name: "Modifier le nom de l’entreprise" });
    expect(filled(button)).toBe(false);
    expect(card.querySelector('[data-slot="card-header"]')?.contains(button)).toBe(true);
    expect(button.closest('[data-slot="section-card-principal"]')).toHaveAttribute(
      "data-does",
      "modify",
    );
    expect(within(card).getByText(settings.company_name)).toBeVisible();
    expect(within(card).getByText("Europe/Paris")).toBeVisible();
    expect(within(card).getAllByRole("button")).toHaveLength(1);
    expectCommandRule(container);
    await expectAccessible(container);
  });

  it("stands in its card with no command for a session that only reads", async () => {
    const { container } = render(
      inFrench(<InstallationCard settings={settings} installation={installation} />),
    );
    const card = screen.getByRole("region", { name: "Installation" });
    expect(within(card).getByText(settings.company_name)).toBeVisible();
    expect(within(card).getByText("Français")).toBeVisible();
    expect(within(card).queryByRole("button")).toBeNull();
    expectCommandRule(container);
    await expectAccessible(container);
  });
});

describe("the correspondence of the actual costs in cards", () => {
  /** The correspondence, editable or read only, in French. */
  function shown(writes: boolean) {
    server.client = fakeClient({});
    return render(inFrench(<ActualCostMapping mapping={mapping} writes={writes} />));
  }

  it("shows a card of the columns read and a card of the columns kept, the five columns in the first", () => {
    shown(true);
    const read = screen.getByRole("region", { name: "Colonnes lues" });
    const kept = screen.getByRole("region", { name: "Colonnes conservées" });
    expect(read).toHaveAttribute("data-slot", "section-card");
    expect(kept).toHaveAttribute("data-slot", "section-card");
    expect(within(read).getAllByRole("group")).toHaveLength(mapping.columns.length);
    expect(within(kept).getAllByRole("group")).toHaveLength(1);
    expect(read.contains(kept)).toBe(false);
    expect(read.compareDocumentPosition(kept) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("bounds each field of a label to a reading width, whatever the width of its card", () => {
    shown(true);
    const fields = screen.getAllByRole("textbox");
    expect(fields.length).toBeGreaterThan(0);
    for (const field of fields) {
      expect(field).toHaveClass("max-w-xl");
    }
  });

  it("sets « Enregistrer la correspondance » filled at the foot, after both cards and in neither", () => {
    const { container } = shown(true);
    const save = screen.getByRole("button", { name: "Enregistrer la correspondance" });
    expect(filled(save)).toBe(true);
    expect(save.closest('[data-slot="section-card"]')).toBeNull();
    const kept = screen.getByRole("region", { name: "Colonnes conservées" });
    expect(kept.compareDocumentPosition(save) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expectCommandRule(container);
  });

  it("reads in the same two cards, with no command, for a session that only reads", async () => {
    const { container } = shown(false);
    expect(screen.getByRole("region", { name: "Colonnes lues" })).toBeVisible();
    expect(screen.getByRole("region", { name: "Colonnes conservées" })).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
    expectCommandRule(container);
    await expectAccessible(container);
  });
});
