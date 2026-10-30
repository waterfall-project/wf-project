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
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  held,
  type Problem,
} from "@/test/fixtures";

import { IdentitySyncScheduleSection } from "./identity-sync-schedule";

type Schedule = components["schemas"]["IdentitySyncSchedule"];

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

// A write of the schedule whose server action rejects once `until` settles — the API out of reach,
// as `fetch` rejects in the browser —; none, and the action asks the fake back.
const failing = vi.hoisted((): { until: Promise<void> | undefined } => ({ until: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("@/api/actions/users", async (original) => {
  const actual = await original<typeof import("@/api/actions/users")>();
  return {
    ...actual,
    setIdentitySyncSchedule: async (
      ...asked: Parameters<typeof actual.setIdentitySyncSchedule>
    ) => {
      if (failing.until === undefined) {
        return actual.setIdentitySyncSchedule(...asked);
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
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(),
}));

const SET = "PUT /identity-sync-schedule";
const witness = example("identity_sync_schedule") as Schedule;

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient({ [SET]: "identity_sync_schedule_set", ...answers }, timing);
  server.client = client;
  return client;
}

/** The section, in French. */
function open(editable = true, schedule: Schedule = witness) {
  render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <IdentitySyncScheduleSection schedule={schedule} editable={editable} />
    </NextIntlClientProvider>,
  );
}

/** Open the form, choose a weekly reading on Monday, and press save. */
async function saveWeekly(): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole("button", { name: "Modifier la périodicité" }));
  const form = screen.getByRole("dialog", { name: "Modifier la périodicité" });
  await userEvent.selectOptions(within(form).getByLabelText("Fréquence"), "weekly");
  await userEvent.selectOptions(within(form).getByLabelText("Jour"), "1");
  await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
  return form;
}

beforeEach(() => {
  process.env.TZ = "Europe/Paris";
});

afterEach(() => {
  refresh.mockClear();
  router.refresh.mockClear();
  failing.until = undefined;
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

  it.each([
    ["the day out of the week", "identity_sync_schedule_weekday_out_of_range"],
    ["the day missing", "identity_sync_schedule_weekday_missing"],
  ] as const)(
    "says at its field the day the server refuses — %s —, the form open to correct it [WF-ADM-0070-A]",
    async (_, refusal) => {
      serve({ [SET]: { problem: example(refusal) as Problem & { status: 422 } } });
      open();
      const form = await saveWeekly();
      const day = within(form).getByLabelText("Jour");
      await vi.waitFor(() => {
        expect(day).toHaveFocus();
      });
      expect(day).toHaveAttribute("aria-invalid", "true");
      expect(within(form).queryByRole("alert")).toBeNull();
      expect(refresh).not.toHaveBeenCalled();
    },
  );

  it("says the version stale under the form, and offers to read the page anew [WF-ADM-0070-A]", async () => {
    serve({
      [SET]: {
        problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 3 } },
      },
    });
    open();
    const form = await saveWeekly();
    await userEvent.click(await within(form).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("keeps its command inactive while a write of the dialog closed is under way, then opens on the version it brings (#661) [WF-ADM-0070-A]", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    open();
    const form = await saveWeekly();
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    const command = screen.getByRole("button", { name: "Modifier la périodicité" });
    expect(command).toHaveFocus();
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAttribute("aria-busy", "true");
    expect(command).toHaveAccessibleDescription("Enregistrement en cours…");
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
    release();
    await vi.waitFor(() => {
      expect(screen.getByRole("region", { name: "Périodicité de la lecture" })).toHaveTextContent(
        "Périodicité enregistrée.",
      );
    });
    expect(command).not.toHaveAttribute("aria-disabled");
    expect(command).not.toHaveAttribute("aria-busy", "true");
    await userEvent.click(command);
    const reopened = screen.getByRole("dialog", { name: "Modifier la périodicité" });
    expect(within(reopened).getByLabelText("Fréquence")).toHaveValue("weekly");
    await userEvent.click(within(reopened).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.body).toMatchObject({ frequency: "weekly", lock_version: 2 });
  });

  it("does not close the opening that follows when the answer of a closed one arrives [WF-ADM-0070-A]", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    open();
    const form = await saveWeekly();
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    release();
    const command = screen.getByRole("button", { name: "Modifier la périodicité" });
    await vi.waitFor(() => {
      expect(command).not.toHaveAttribute("aria-disabled");
    });
    await userEvent.click(command);
    expect(screen.getByRole("dialog", { name: "Modifier la périodicité" })).toBeVisible();
    await new Promise((settle) => setTimeout(settle, 20));
    expect(screen.getByRole("dialog", { name: "Modifier la périodicité" })).toBeVisible();
  });

  it("frees its command once a write of the dialog closed is rejected, the API out of reach, and says so [WF-ADM-0070-A]", async () => {
    let settle: () => void = () => undefined;
    failing.until = new Promise<void>((resolve) => {
      settle = resolve;
    });
    serve();
    open();
    const form = await saveWeekly();
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    const command = screen.getByRole("button", { name: "Modifier la périodicité" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    settle();
    expect(await screen.findByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(command).not.toHaveAttribute("aria-disabled");
  });

  it("keeps the reading when the answer is older than it (lock_version) [WF-ADM-0070-A]", async () => {
    serve();
    open(true, { ...witness, lock_version: 5 });
    await saveWeekly();
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    const section = screen.getByRole("region", { name: "Périodicité de la lecture" });
    expect(section).toHaveTextContent("FréquenceQuotidienne");
    expect(section).not.toHaveTextContent("Hebdomadaire");
  });
});
