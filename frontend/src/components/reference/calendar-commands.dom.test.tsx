// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { type Calendar, DAYS } from "./resource-grids";
import { CalendarList, type DayBounds } from "./resource-lists";

// The commands of the calendars (EP-02/L43b, EP-14/L43g), the forms of the nodes and of the roles
// being those of `resource-commands.dom.test.tsx`. The server of Next, as far as the list needs it:
// the fake back, the page rendered again once a calendar is written, the address it reads.
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

const CALENDARS = "POST /reference/calendars";
const CALENDAR = "PATCH /reference/calendars/{calendar_id}";
const DEFAULT = "PUT /reference/calendars/{calendar_id}/default";

const NO_QUERY = { sort: undefined, search: undefined };
const NO_BOUNDS = { min: undefined, max: undefined };
const calendars = example("calendars_with_inactive") as { items: Calendar[]; meta: ListPage };

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({
    [CALENDARS]: { example: "calendar_created", status: 201 },
    [CALENDAR]: "calendar_updated",
    [DEFAULT]: "calendar_default",
    ...answers,
  });
  server.client = client;
  return client;
}

/**
 * The calendars, in French, the active ones unless told, for a session that may write them — their
 * commands listed.
 */
function calendarList(
  rows: readonly Calendar[] = calendars.items.filter((calendar) => calendar.is_active),
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <CalendarList
          rows={rows}
          page={calendars.meta}
          query={NO_QUERY}
          preferences={undefined}
          readsInactive
          editable
          state={undefined}
          hours={Object.fromEntries(DAYS.map((day) => [day, NO_BOUNDS])) as DayBounds}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The calls the list made of the fake back. */
function writes(client: FakeClient) {
  return client.calls.map(({ route, path, body }) => ({ route, path, body }));
}

/** What the regions of the screen announce. */
function announced(): (string | null)[] {
  return screen.getAllByRole("status").map((status) => status.textContent);
}

/** Open a dialog by the command named, and give it back by its name. */
async function opened(command: string, name: string): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole("button", { name: command }));
  return screen.getByRole("dialog", { name });
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  refresh.mockClear();
  router.refresh.mockClear();
});

describe("the calendars", () => {
  it("creates a calendar by its seven values of hours, from Monday, and asks nothing else [WF-REF-0110-A]", async () => {
    const client = serve();
    render(calendarList());
    const form = await opened("Nouveau calendrier", "Nouveau calendrier");
    // Un calendrier se saisit par sept valeurs d'heures, du lundi au dimanche, et aucune autre
    // donnée n'est demandée.
    expect(
      within(form)
        .getAllByRole("textbox")
        .map((field) => (field as HTMLInputElement).labels?.[0]?.textContent),
    ).toEqual(["Libellé", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]);
    expect(within(form).queryByRole("combobox")).toBeNull();
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé" }),
      "Semaine de trente-cinq heures",
    );
    for (const day of ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]) {
      await userEvent.type(within(form).getByRole("textbox", { name: day }), "7");
    }
    for (const day of ["Samedi", "Dimanche"]) {
      await userEvent.type(within(form).getByRole("textbox", { name: day }), "0");
    }
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(writes(client)[0]?.body).toEqual({
      label: "Semaine de trente-cinq heures",
      weekly_hours: {
        monday: "7",
        tuesday: "7",
        wednesday: "7",
        thursday: "7",
        friday: "7",
        saturday: "0",
        sunday: "0",
      },
    });
    expect(announced()).toContain("« Semaine de trente-cinq heures » créé.");
  });

  it("modifies a calendar from the version read, its hours shown in the language of the reader", async () => {
    const client = serve();
    render(calendarList());
    const form = await opened(
      "Modifier « Semaine de quatre jours »",
      "Modifier « Semaine de quatre jours »",
    );
    expect(within(form).getByRole("textbox", { name: "Lundi" })).toHaveValue("10");
    const label = within(form).getByRole("textbox", { name: "Libellé" });
    await userEvent.clear(label);
    await userEvent.type(label, "Semaine de quatre jours de dix heures");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toMatchObject({
      label: "Semaine de quatre jours de dix heures",
      weekly_hours: { monday: "10", friday: "0" },
      lock_version: 1,
    });
  });

  it("designates an active calendar by default from its row, reads the page anew, and shows the answer in its row", async () => {
    const client = serve();
    render(calendarList());
    // The default calendar is marked, and offers no designation.
    expect(
      screen.queryByRole("button", { name: "Désigner « Semaine standard » par défaut" }),
    ).toBeNull();
    await userEvent.click(
      screen.getByRole("button", { name: "Désigner « Semaine de quatre jours » par défaut" }),
    );
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // Withdrawing the designation from the one before is the server's: the page read anew shows it.
    expect(writes(client)).toEqual([
      {
        route: DEFAULT,
        path: "/reference/calendars/01926f3a-7c00-7000-8000-000000000482/default",
        body: { lock_version: 1 },
      },
    ]);
    expect(announced()).toContain("« Semaine de quatre jours » désigné calendrier par défaut.");
    const row = document.querySelector('td[data-row="0"][data-column="is_default"]');
    expect(row).toHaveTextContent("Calendrier par défaut");
  });

  it.each([
    // Deactivated meanwhile: the condition its command now lacks.
    [
      "calendar_default_refused",
      { problem: example("calendar_default_refused") as Problem & { status: 409 } },
      "L’état actuel ne permet pas cette opération. Condition non remplie : calendrier actif.",
      false,
    ],
    // Modified meanwhile: the version sent is stale, and the page is offered to be read anew.
    [
      "calendar_default_stale",
      { problem: example("calendar_default_stale") as Problem & { status: 412 } },
      "Quelqu’un a modifié cette donnée entre-temps",
      true,
    ],
  ] satisfies [string, FakeAnswers[typeof DEFAULT], string, boolean][])(
    "says the refusal %s of a designation above the list, the row as the page read it",
    async (_refusal, answer, said, reload) => {
      serve({ [DEFAULT]: answer });
      render(calendarList());
      await userEvent.click(
        screen.getByRole("button", {
          name: "Désigner «\u00a0Semaine de quatre jours\u00a0» par défaut",
        }),
      );
      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(said);
      expect(within(alert).queryByRole("button", { name: "Recharger" }) !== null).toBe(reload);
      expect(refresh).not.toHaveBeenCalled();
      expect(
        document.querySelector('td[data-row="0"][data-column="is_default"]'),
      ).toHaveTextContent("Désigner");
    },
  );

  it("presents the designation of a deactivated calendar unavailable, with its condition, a press saying it without asking anything", async () => {
    const client = serve();
    render(calendarList(calendars.items));
    const command = screen.getByRole("button", {
      name: "Désigner « Semaine de trente-neuf heures » par défaut",
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription("Condition non remplie\u00a0: calendrier actif.");
    await userEvent.click(command);
    expect(announced()).toContain(
      "La désignation de «\u00a0Semaine de trente-neuf heures\u00a0» par défaut est indisponible. Condition non remplie\u00a0: calendrier actif.",
    );
    expect(client.calls).toEqual([]);
  });

  it.each([
    // The thirty-nine-hour week, deactivated, among the rows: named by its identifier.
    ["shown", calendars.items, "Déjà porté par «\u00a0Semaine de trente-neuf heures\u00a0»."],
    // The active ones alone: nothing names it.
    [
      "not shown",
      calendars.items.filter((calendar) => calendar.is_active),
      "Déjà porté par un autre calendrier.",
    ],
  ])(
    "says at the label the refusal of a label another calendar holds, deactivated ones counted, the holder %s by the list [WF-REF-0110-A]",
    async (_shown, rows, holder) => {
      serve({
        [CALENDARS]: { problem: example("calendar_label_taken") as Problem & { status: 409 } },
      });
      render(calendarList(rows));
      const form = await opened("Nouveau calendrier", "Nouveau calendrier");
      const label = within(form).getByRole("textbox", { name: "Libellé" });
      await userEvent.type(label, "Semaine de trente-neuf heures");
      for (const day of ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]) {
        await userEvent.type(within(form).getByRole("textbox", { name: day }), "0");
      }
      await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
      // Deux calendriers de même libellé sont refusés.
      await vi.waitFor(() => {
        expect(label).toHaveFocus();
      });
      expect(label).toHaveAccessibleDescription(`Cet élément existe déjà. ${holder}`);
      expect(refresh).not.toHaveBeenCalled();
    },
  );

  it("says at each day the hours the server refuses out of zero to twenty-four, with the bound crossed", async () => {
    serve({
      [CALENDAR]: { problem: example("calendar_hours_refused") as Problem & { status: 422 } },
    });
    render(calendarList());
    const form = await opened(
      "Modifier « Semaine de quatre jours »",
      "Modifier « Semaine de quatre jours »",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    const monday = within(form).getByRole("textbox", { name: "Lundi" });
    await vi.waitFor(() => {
      expect(monday).toHaveFocus();
    });
    expect(monday).toHaveAccessibleDescription(
      "La valeur sort des limites admises. Valeur maximale\u00a0: 24.",
    );
    expect(within(form).getByRole("textbox", { name: "Samedi" })).toHaveAccessibleDescription(
      "La valeur sort des limites admises. Valeur minimale\u00a0: 0.",
    );
    expect(within(form).getByRole("textbox", { name: "Mardi" })).not.toHaveAttribute(
      "aria-invalid",
    );
  });

  it("tells under the form the modification of a calendar from a stale version, with the offer to read the page anew", async () => {
    serve({
      [CALENDAR]: { problem: example("calendar_update_stale") as Problem & { status: 412 } },
    });
    render(calendarList());
    const form = await opened(
      "Modifier « Semaine de quatre jours »",
      "Modifier « Semaine de quatre jours »",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    const alert = await within(form).findByRole("alert");
    expect(alert).toHaveTextContent("Quelqu’un a modifié cette donnée entre-temps");
    expect(within(alert).getByRole("button", { name: "Recharger" })).toBeInTheDocument();
  });

  it("presents the deactivation of the default calendar unavailable, with its condition [WF-REF-0120-A]", async () => {
    const client = serve();
    render(calendarList());
    // La désactivation du calendrier par défaut est refusée tant qu'un autre n'a pas été désigné.
    const command = screen.getByRole("button", {
      name: "Désactiver « Semaine standard »",
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(
      "Condition non remplie : calendrier autre que celui par défaut.",
    );
    await userEvent.click(command);
    expect(client.calls).toEqual([]);
  });
});
