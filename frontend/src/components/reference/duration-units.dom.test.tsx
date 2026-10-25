// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, fakeClient, type Problem } from "@/test/fixtures";

import { DurationUnitFacts } from "./resource-lists";

type DurationUnits = components["schemas"]["DurationUnits"];

// The server of Next, as far as the form needs it: the fake back, and the page rendered again.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(),
}));

const UPDATE = "PUT /reference/duration-units";
const witness = example("duration_units") as DurationUnits;
const COMMAND = "Modifier les unités de durée";

afterEach(() => {
  refresh.mockClear();
  router.refresh.mockClear();
});

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers) {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** The section of the units of duration, in French, for a session that may or may not modify. */
function show(editable: boolean) {
  render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <DurationUnitFacts units={witness} editable={editable} />
    </NextIntlClientProvider>,
  );
}

/** Open the form of the three constants. */
async function open(): Promise<HTMLElement> {
  show(true);
  await userEvent.click(screen.getByRole("button", { name: COMMAND }));
  return screen.getByRole("dialog", { name: COMMAND });
}

/** Put a text in place of what a field holds. */
async function retype(control: HTMLElement, text: string) {
  await userEvent.clear(control);
  await userEvent.type(control, text);
}

describe("the units of duration", () => {
  it("offer no command to a session that may not modify the settings of the resources", () => {
    show(false);
    expect(screen.queryByRole("button", { name: COMMAND })).toBeNull();
    expect(screen.getByText("Heures par jour").nextElementSibling).toHaveTextContent("8");
  });

  it("open a form of the three constants in the decimals of the language, and say what the change does to the schedules under the fields", async () => {
    const form = await open();
    expect(within(form).getByRole("textbox", { name: "Heures par jour" })).toHaveValue("8");
    expect(within(form).getByRole("textbox", { name: "Heures par semaine" })).toHaveValue("40");
    expect(within(form).getByRole("textbox", { name: "Jours par mois" })).toHaveValue("20");
    expect(form).toHaveTextContent(
      "Le changement vaut pour tous les projets : les plannings des révisions en cours sont recalculés ; une révision marquée garde les heures qu’elle a calculées.",
    );
    await expectAccessible(form);
  });

  it("send the constants as the contract writes them with the version read, and show the answer in place of the reading", async () => {
    const client = serve({ [UPDATE]: "duration_units_updated" });
    const form = await open();
    await retype(within(form).getByRole("textbox", { name: "Heures par jour" }), "7,5");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(client.calls.map(({ route, body }) => ({ route, body }))).toEqual([
      {
        route: UPDATE,
        body: { hours_per_day: "7.5", hours_per_week: "40", days_per_month: "20", lock_version: 1 },
      },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    // The answer of the server, not what was typed.
    expect(screen.getByText("Heures par jour").nextElementSibling).toHaveTextContent("7");
    expect(screen.getByText("Heures par semaine").nextElementSibling).toHaveTextContent("35");
    expect(screen.getByRole("button", { name: COMMAND })).toHaveFocus();
  });

  it("say at its field a constant the server refuses, and give it the focus", async () => {
    serve({ [UPDATE]: { problem: example("duration_units_zero") as Problem & { status: 422 } } });
    const form = await open();
    await retype(within(form).getByRole("textbox", { name: "Heures par jour" }), "0");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    const field = within(form).getByRole("textbox", { name: "Heures par jour" });
    await vi.waitFor(() => {
      expect(field).toHaveFocus();
    });
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(form).toHaveTextContent("La constante doit être strictement positive.");
    expect(within(form).queryByRole("alert")).toBeNull();
  });

  it("refuse a constant that is no number before asking the server", async () => {
    const client = serve({ [UPDATE]: "duration_units_updated" });
    const form = await open();
    await retype(within(form).getByRole("textbox", { name: "Jours par mois" }), "abc");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(within(form).getByRole("textbox", { name: "Jours par mois" })).toHaveFocus();
    expect(client.calls).toEqual([]);
  });

  it("say the version stale under the form and offer to read the page anew", async () => {
    serve({ [UPDATE]: { problem: example("duration_units_stale") as Problem & { status: 412 } } });
    const form = await open();
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await userEvent.click(await within(form).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });
});
