// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { TimeZoneProvider } from "@/installation/time-zone";
import { example, fakeClient } from "@/test/fixtures";

import { Kanban } from "./kanban";
import { columnsOf, type StartableTasks } from "./kanban-cards";

// The date a card asks for the event of a gesture is proposed in the time zone of the installation
// (WF-PLA-0130), whatever the zone of the workstation: the cards are those of the example
// `startable_tasks` of the contract.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: vi.fn(), replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/kanban",
  useSearchParams: () => new URLSearchParams(),
}));

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the date of the event proposed on a card of the Kanban", () => {
  it("is the day of the time zone of the installation, not the universal one [WF-PLA-0130-A]", async () => {
    // At 23:30 universal time, Paris is already on the next day.
    vi.setSystemTime(new Date("2026-11-13T23:30:00Z"));
    server.client = fakeClient({});
    const all = columnsOf(example("startable_tasks") as StartableTasks);
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <TimeZoneProvider timeZone="Europe/Paris">
          <Kanban
            columns={{ not_started: all.not_started.slice(0, 4), started: [], completed: [] }}
            structure={{
              project_id: "01926f3a-7c00-7000-8000-000000000001",
              revision_id: "01926f3a-7c00-7000-8000-000000000102",
              structure_id: "01926f3a-7c00-7000-8000-000000000201",
            }}
            remaining="/projects/p/revisions/r/remaining"
            filters={{ text: "", ready: false }}
          />
        </TimeZoneProvider>
      </NextIntlClientProvider>,
    );

    const label = "Réception usine";
    const item = screen.getByText(label, { selector: "span" }).closest("li");
    if (item === null) {
      throw new Error(`no card for ${label}`);
    }
    const user = userEvent.setup();
    await user.click(item);
    await user.click(within(item).getByRole("button", { name: `Gestes de la tâche ${label}` }));
    await user.click(await screen.findByRole("menuitem", { name: /^Terminer/ }));

    expect(await within(item).findByLabelText("Date de l’événement")).toHaveValue("2026-11-14");
  });
});
