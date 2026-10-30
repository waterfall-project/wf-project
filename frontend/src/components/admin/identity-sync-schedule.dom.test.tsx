// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { IdentitySyncScheduleSection } from "./identity-sync-schedule";

type Schedule = components["schemas"]["IdentitySyncSchedule"];

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(),
}));

const SET = "PUT /identity-sync-schedule";
const witness = example("identity_sync_schedule") as Schedule;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({ [SET]: "identity_sync_schedule_set", ...answers });
  server.client = client;
  return client;
}

/** The section, in French. */
function open(editable = true) {
  render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <IdentitySyncScheduleSection schedule={witness} editable={editable} />
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  process.env.TZ = "Europe/Paris";
});

afterEach(() => {
  refresh.mockClear();
});

describe("the periodicity of the reading of the accounts", () => {
  it("states the periodicity read, daily by default, its time in universal time [WF-ADM-0070-A]", async () => {
    serve();
    open();
    const section = screen.getByRole("region", { name: "Périodicité de la lecture" });
    expect(section).toHaveTextContent("ÉtatActiveFréquenceQuotidienneHeure01:30 UTC");
    await expectAccessible(section);
  });

  it("offers no command to a session that may not modify the accounts [WF-ADM-0070-A]", () => {
    serve();
    open(false);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("sets the periodicity whole from the version read, shows the answer in place of the reading, and reads the page anew [WF-ADM-0070-A]", async () => {
    const client = serve();
    open();
    await userEvent.click(screen.getByRole("button", { name: "Modifier la périodicité" }));
    const form = screen.getByRole("dialog", { name: "Modifier la périodicité" });
    await userEvent.selectOptions(within(form).getByLabelText("Fréquence"), "weekly");
    await userEvent.selectOptions(within(form).getByLabelText("Jour"), "1");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(client.calls.map(({ route, body }) => ({ route, body }))).toEqual([
      { route: SET, body: { ...witness, frequency: "weekly", weekday: 1 } },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    const section = screen.getByRole("region", { name: "Périodicité de la lecture" });
    expect(section).toHaveTextContent("FréquenceHebdomadaireJourLundi");
    expect(section).toHaveTextContent("Périodicité enregistrée.");
  });

  it("asks a day of a weekly reading, and the form asks nothing without it [WF-ADM-0070-A]", async () => {
    const client = serve();
    open();
    await userEvent.click(screen.getByRole("button", { name: "Modifier la périodicité" }));
    const form = screen.getByRole("dialog", { name: "Modifier la périodicité" });
    await userEvent.selectOptions(within(form).getByLabelText("Fréquence"), "weekly");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(client.calls).toEqual([]);
    expect(screen.getByRole("dialog")).toBeVisible();
  });
});
