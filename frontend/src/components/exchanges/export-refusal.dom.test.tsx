// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { Revision } from "@/components/context/read-only";
import { TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";

import { ExportForm } from "./export-form";
import { exportOffers } from "./offers";

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient({}) }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

describe("the request of an export the revision lists unavailable", () => {
  it("forgets the refusal of a press when another kind, unavailable too, is chosen [WF-IHM-0090-A]", async () => {
    const revision = structuredClone(example("revision") as Revision);
    for (const command of revision.available_commands) {
      if (command.command.startsWith("export_")) {
        command.is_available = false;
        command.missing_conditions = ["revision_marked"];
      }
    }
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <TaskTracker>
          <ExportForm projectId={PROJECT} revisionId={REVISION} offers={exportOffers(revision)} />
        </TaskTracker>
      </NextIntlClientProvider>,
    );
    const form = screen.getByRole("form", { name: "Demander un export" });
    const kinds = within(form).getByLabelText("Fichier à exporter");
    await userEvent.selectOptions(kinds, "Devis");
    await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
    expect(within(form).getByRole("alert")).toHaveTextContent("révision marquée");
    await userEvent.selectOptions(kinds, "Reste à engager");
    expect(within(form).queryByRole("alert")).toBeNull();
    await userEvent.click(within(form).getByRole("button", { name: "Demander l’export" }));
    expect(within(form).getByRole("alert")).toHaveTextContent("révision marquée");
  });
});
