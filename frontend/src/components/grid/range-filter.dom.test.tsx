// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";

import type { Bounds, FigureKind } from "./filters";
import { PendingAddress } from "./pending-address";
import { type RangeColumn, RangeFilter, type RangeScope, type SideRefusals } from "./range-filter";
import { ValuesFilter } from "./values-filter";

// The server of Next, as far as the filter needs it: the address it reads and the navigations it
// asks.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const NONE: Bounds = { min: undefined, max: undefined };

/** The bounds of the monthly hours and of the headcount of the roles, as the address sets them. */
function roleColumns(
  hours: Bounds = NONE,
  headcount: Bounds = NONE,
  refused?: SideRefusals,
): RangeColumn[] {
  return [
    { column: "role_monthly_hours", label: "Heures par mois", bounds: hours, refused },
    { column: "role_headcount", label: "Effectif", bounds: headcount },
  ];
}

/** The filter of the roles, in a language, sharing the address last asked as the page does. */
function filter(
  columns: readonly RangeColumn[],
  options: {
    readonly locale?: Locale;
    readonly scope?: RangeScope;
    readonly kind?: FigureKind;
  } = {},
): ReactNode {
  const locale = options.locale ?? "fr";
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PendingAddress>
        <RangeFilter
          label="Bornes des rôles"
          kind={options.kind ?? (options.scope === undefined ? "decimal" : "money")}
          columns={columns}
          scope={options.scope}
          page="role_offset"
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The address of the last navigation the filter asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

beforeEach(() => {
  page.search = "";
});

afterEach(() => {
  router.push.mockClear();
});

describe("the filter of a list on the bounds of its figures", () => {
  it("writes each bound entered as the contract writes it, under the names of the column, back to the first page, the rest kept [WF-IHM-0130-A]", async () => {
    page.search = "role_sort_by=label&role_offset=50&role_headcount_max=9";
    render(filter(roleColumns(NONE, { min: undefined, max: "9" })));
    const form = screen.getByRole("form", { name: "Bornes des rôles" });
    const least = within(form).getByRole("textbox", { name: "Heures par mois, min." });
    const most = within(form).getByRole("textbox", { name: "Effectif, max." });
    expect(most).toHaveValue("9");
    // As French writes a number: spaces between the thousands, a comma before the decimals.
    await userEvent.type(least, "300 000,5");
    await userEvent.clear(most);
    await userEvent.click(within(form).getByRole("button", { name: "Filtrer" }));
    expect(lastAddress()).toBe(
      "/reference/resources?role_sort_by=label&role_monthly_hours_min=300000.5",
    );
  });

  it("writes the bounds as the contract writes them whatever the language", async () => {
    render(filter(roleColumns(), { locale: "en" }));
    await userEvent.type(
      screen.getByRole("textbox", { name: "Heures par mois, max" }),
      "1,234.5{Enter}",
    );
    expect(lastAddress()).toBe("/reference/resources?role_monthly_hours_max=1234.5");
  });

  it("names each field by the column and the side written beside it", () => {
    render(filter(roleColumns()));
    const group = screen.getByRole("group", { name: "Heures par mois" });
    expect(group).toHaveTextContent("Heures par moismin.max.");
    // The name holds what the eye reads (WCAG 2.5.3).
    expect(
      within(group)
        .getAllByRole("textbox")
        .map((field) => field.getAttribute("aria-label")),
    ).toEqual(["Heures par mois, min.", "Heures par mois, max."]);
  });

  it("says at its field a bound that is no number of the language, gives it the focus, and asks nothing", async () => {
    render(filter(roleColumns()));
    const least = screen.getByRole("textbox", { name: "Effectif, min." });
    await userEvent.type(least, "1.5");
    // Sent from another field: the focus goes to the first one wrong.
    await userEvent.type(screen.getByRole("textbox", { name: "Heures par mois, max." }), "{Enter}");
    expect(router.push).not.toHaveBeenCalled();
    expect(least).toHaveAttribute("aria-invalid", "true");
    expect(least).toHaveAccessibleDescription("Ce n’est pas un nombre valide.");
    expect(least).toHaveFocus();
    // Corrected, it is asked.
    await userEvent.clear(least);
    await userEvent.type(least, "1,5{Enter}");
    expect(lastAddress()).toBe("/reference/resources?role_headcount_min=1.5");
    expect(least).not.toHaveAttribute("aria-invalid");
  });

  it("says at its field the upper bound the server refused for preceding the lower one, by the lower one it names", async () => {
    page.search = "role_monthly_hours_min=1000&role_monthly_hours_max=500";
    const { container } = render(
      filter(
        roleColumns({ min: "1000", max: "500" }, NONE, {
          max: { code: "VALUE_OUT_OF_RANGE", minimum: "1000" },
        }),
      ),
    );
    const most = screen.getByRole("textbox", { name: "Heures par mois, max." });
    expect(most).toHaveValue("500");
    expect(most).toHaveAttribute("aria-invalid", "true");
    // The list comes back refused: the focus on the bound refused.
    expect(most).toHaveFocus();
    expect(most).toHaveAccessibleDescription(
      "La borne supérieure ne peut précéder la borne inférieure, 1 000.",
    );
    expect(screen.getByRole("textbox", { name: "Heures par mois, min." })).not.toHaveAttribute(
      "aria-invalid",
    );
    await expectAccessible(container);
  });

  it("lifts every bound it sets at once, and offers it only while one is set", async () => {
    page.search = "role_monthly_hours_min=10&role_headcount_max=3&role_offset=50";
    const { rerender } = render(
      filter(roleColumns({ min: "10", max: undefined }, { min: undefined, max: "3" })),
    );
    await userEvent.click(screen.getByRole("button", { name: "Lever les bornes" }));
    expect(lastAddress()).toBe("/reference/resources");
    page.search = "";
    rerender(filter(roleColumns()));
    expect(screen.queryByRole("button", { name: "Lever les bornes" })).toBeNull();
    expect(screen.getByRole("textbox", { name: "Heures par mois, min." })).toHaveValue("");
  });

  it("sets the fields anew when the address changes the bounds, back in the history", async () => {
    page.search = "role_monthly_hours_min=10";
    const { rerender } = render(filter(roleColumns({ min: "10", max: undefined })));
    const least = () => screen.getByRole("textbox", { name: "Heures par mois, min." });
    await userEvent.type(least(), "0");
    expect(least()).toHaveValue("100");
    page.search = "role_monthly_hours_min=20.5";
    rerender(filter(roleColumns({ min: "20.5", max: undefined })));
    expect(least()).toHaveValue("20,5");
  });

  it("writes the year whose rate is bounded with the bounds, and lifts it with the last [WF-IHM-0130-A]", async () => {
    const scope: RangeScope = {
      name: "rate_year",
      label: "Année du taux",
      choices: ["2025", "2026"].map((year) => ({ value: year, text: year })),
      chosen: undefined,
    };
    const columns: RangeColumn[] = [{ column: "rate", label: "Taux horaire", bounds: NONE }];
    const { rerender } = render(filter(columns, { scope }));
    const year = screen.getByRole("combobox", { name: "Année du taux" });
    // The first year offered, when the address names none.
    expect(year).toHaveValue("2025");
    await userEvent.selectOptions(year, "2026");
    await userEvent.type(screen.getByRole("textbox", { name: "Taux horaire, min." }), "110{Enter}");
    expect(lastAddress()).toBe("/reference/resources?rate_min=110&rate_year=2026");
    // An amount keeps two decimals at most.
    const most = screen.getByRole("textbox", { name: "Taux horaire, max." });
    await userEvent.type(most, "150,555{Enter}");
    expect(router.push).toHaveBeenCalledOnce();
    expect(most).toHaveAttribute("aria-invalid", "true");
    expect(most).toHaveAccessibleDescription("Deux décimales au plus.");
    page.search = "rate_min=110&rate_year=2026";
    rerender(
      filter(
        [
          {
            ...columns[0],
            column: "rate",
            label: "Taux horaire",
            bounds: { min: "110", max: undefined },
          },
        ],
        {
          scope: { ...scope, chosen: "2026" },
        },
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Lever les bornes" }));
    expect(lastAddress()).toBe("/reference/resources");
  });
});

describe("the entry of the bounds, dated by the address (#553)", () => {
  const least = () => screen.getByRole("textbox", { name: "Heures par mois, min." });
  const most = () => screen.getByRole("textbox", { name: "Heures par mois, max." });

  it("keeps the focus on the field that sent the bounds, and on the button, once the address arrives", async () => {
    const { rerender } = render(filter(roleColumns()));
    const field = least();
    await userEvent.type(field, "10{Enter}");
    expect(lastAddress()).toBe("/reference/resources?role_monthly_hours_min=10");
    // The address sent arrives: the form stays, and the field with the focus and the bound.
    page.search = "role_monthly_hours_min=10";
    rerender(filter(roleColumns({ min: "10", max: undefined })));
    expect(least()).toBe(field);
    expect(field).toHaveFocus();
    expect(field).toHaveValue("10");
    // Sent by its button, the next bound keeps the focus on the button.
    await userEvent.type(most(), "20");
    const apply = screen.getByRole("button", { name: "Filtrer" });
    await userEvent.click(apply);
    page.search = "role_monthly_hours_min=10&role_monthly_hours_max=20";
    rerender(filter(roleColumns({ min: "10", max: "20" })));
    expect(screen.getByRole("button", { name: "Filtrer" })).toBe(apply);
    expect(apply).toHaveFocus();
    expect(most()).toHaveValue("20");
  });

  it("keeps a bound typed while another was on its way, once it arrives, and none typed over the address « Précédent » came back to (#557)", async () => {
    const { rerender } = render(filter(roleColumns()));
    await userEvent.type(least(), "10{Enter}");
    // Typed before the server answers for the least.
    await userEvent.type(most(), "20");
    page.search = "role_monthly_hours_min=10";
    rerender(filter(roleColumns({ min: "10", max: undefined })));
    expect(least()).toHaveValue("10");
    expect(most()).toHaveValue("20");
    expect(most()).toHaveFocus();
    await userEvent.type(most(), "{Enter}");
    expect(lastAddress()).toBe(
      "/reference/resources?role_monthly_hours_min=10&role_monthly_hours_max=20",
    );
    page.search = "role_monthly_hours_min=10&role_monthly_hours_max=20";
    rerender(filter(roleColumns({ min: "10", max: "20" })));
    // « Précédent », a bound typed and given up, then « Suivant »: the bounds of the address.
    page.search = "role_monthly_hours_min=10";
    rerender(filter(roleColumns({ min: "10", max: undefined })));
    await userEvent.type(most(), "99");
    page.search = "role_monthly_hours_min=10&role_monthly_hours_max=20";
    rerender(filter(roleColumns({ min: "10", max: "20" })));
    expect(most()).toHaveValue("20");
  });

  it("shows a bound sent while another was on its way as the address writes it, once it arrives (#557)", async () => {
    const { rerender } = render(filter(roleColumns()));
    await userEvent.type(least(), "10{Enter}");
    await userEvent.type(most(), "20,5  {Enter}");
    expect(lastAddress()).toBe(
      "/reference/resources?role_monthly_hours_min=10&role_monthly_hours_max=20.5",
    );
    page.search = "role_monthly_hours_min=10&role_monthly_hours_max=20.5";
    rerender(filter(roleColumns({ min: "10", max: "20.5" })));
    expect(most()).toHaveValue("20,5");
  });

  it("keeps a bound typed while another was on its way, once a filter composed on it arrives (#557)", async () => {
    // The bounds and a filter of the same list, sharing the address last asked as the page does.
    const screenAt = (search: string) => {
      page.search = search;
      const address = new URLSearchParams(search);
      const min = address.get("role_monthly_hours_min") ?? undefined;
      return (
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
          <PendingAddress>
            <RangeFilter
              label="Bornes des rôles"
              kind="decimal"
              columns={roleColumns({ min, max: undefined })}
            />
            <ValuesFilter
              name="role_is_active"
              label="État"
              every="Tous les états"
              values={[{ value: "true", text: "Actifs" }]}
              chosen={address.get("role_is_active") === "true" ? ["true"] : []}
              exhaustive={false}
            />
          </PendingAddress>
        </NextIntlClientProvider>
      );
    };
    const { rerender } = render(screenAt(""));
    await userEvent.type(least(), "10{Enter}");
    // Typed before the server answers, then a filter chosen, which carries the bound sent.
    await userEvent.type(most(), "20");
    await userEvent.click(screen.getByRole("button", { name: "Actifs" }));
    expect(lastAddress()).toBe(
      "/reference/resources?role_monthly_hours_min=10&role_is_active=true",
    );
    rerender(screenAt("role_monthly_hours_min=10&role_is_active=true"));
    expect(least()).toHaveValue("10");
    expect(most()).toHaveValue("20");
  });

  it("forgets what was typed and not sent, and what it got wrong, when the address comes back to the bounds it was typed over", async () => {
    page.search = "role_monthly_hours_min=10";
    const { rerender } = render(filter(roleColumns({ min: "10", max: undefined })));
    await userEvent.type(least(), "0");
    await userEvent.type(most(), "abc{Enter}");
    expect(most()).toHaveAttribute("aria-invalid", "true");
    expect(router.push).not.toHaveBeenCalled();
    // Back in the history to other bounds, then forward to those the entry was typed over: they
    // show the address, the entry and its fault given up.
    page.search = "role_monthly_hours_min=20";
    rerender(filter(roleColumns({ min: "20", max: undefined })));
    expect(least()).toHaveValue("20");
    page.search = "role_monthly_hours_min=10";
    rerender(filter(roleColumns({ min: "10", max: undefined })));
    expect(least()).toHaveValue("10");
    expect(most()).toHaveValue("");
    expect(most()).not.toHaveAttribute("aria-invalid");
  });

  it("gives the focus to the bound the server refuses each time a list comes back refused, the same side refused again", async () => {
    const inverted = (min: string, max: string) =>
      filter(
        roleColumns({ min, max }, NONE, { max: { code: "VALUE_OUT_OF_RANGE", minimum: min } }),
      );
    page.search = "role_monthly_hours_min=1000&role_monthly_hours_max=500";
    const { rerender } = render(inverted("1000", "500"));
    expect(most()).toHaveFocus();
    // Sent again by its button, still below the same lower bound: the list comes back with the
    // same refusal of the same side, which takes the focus anew.
    await userEvent.clear(most());
    await userEvent.type(most(), "400");
    await userEvent.click(screen.getByRole("button", { name: "Filtrer" }));
    expect(lastAddress()).toBe(
      "/reference/resources?role_monthly_hours_min=1000&role_monthly_hours_max=400",
    );
    expect(screen.getByRole("button", { name: "Filtrer" })).toHaveFocus();
    page.search = "role_monthly_hours_min=1000&role_monthly_hours_max=400";
    rerender(inverted("1000", "400"));
    expect(most()).toHaveFocus();
    expect(most()).toHaveValue("400");
    expect(most()).toHaveAccessibleDescription(
      "La borne supérieure ne peut précéder la borne inférieure, 1 000.",
    );
  });

  it("gives the focus to the bound typed wrong in the send, not to the choice of the year the server refused before", async () => {
    const scope: RangeScope = {
      name: "rate_year",
      label: "Année du taux",
      choices: [{ value: "2026", text: "2026" }],
      chosen: "2026",
      refused: { code: "VALUE_REQUIRED" },
    };
    page.search = "rate_min=100";
    render(
      filter([{ column: "rate", label: "Taux horaire", bounds: { min: "100", max: undefined } }], {
        scope,
      }),
    );
    const year = screen.getByRole("combobox", { name: "Année du taux" });
    expect(year).toHaveFocus();
    const most = screen.getByRole("textbox", { name: "Taux horaire, max." });
    await userEvent.type(most, "abc{Enter}");
    expect(router.push).not.toHaveBeenCalled();
    // The year is still refused, and comes first in the form: the bound typed wrong takes the focus.
    expect(year).toHaveAttribute("aria-invalid", "true");
    expect(most).toHaveAttribute("aria-invalid", "true");
    await userEvent.click(screen.getByRole("button", { name: "Filtrer" }));
    expect(most).toHaveFocus();
  });

  it("gives the focus to the least of the first column once the button that lifted the bounds is gone", async () => {
    page.search = "role_monthly_hours_max=500&role_headcount_min=2";
    const { rerender } = render(
      filter(roleColumns({ min: undefined, max: "500" }, { min: "2", max: undefined })),
    );
    await userEvent.click(screen.getByRole("button", { name: "Lever les bornes" }));
    expect(lastAddress()).toBe("/reference/resources");
    // The address lifted arrives: the button is gone, the focus on a field that stays, emptied.
    page.search = "";
    rerender(filter(roleColumns()));
    expect(screen.queryByRole("button", { name: "Lever les bornes" })).toBeNull();
    expect(least()).toHaveFocus();
    expect(least()).toHaveValue("");
    expect(document.body).not.toHaveFocus();
  });

  it("keeps what is typed, and the focus, through a change of the address the form does not write", async () => {
    // A list refused: the bound refused takes the focus when it comes back, once.
    page.search = "role_monthly_hours_min=1000&role_monthly_hours_max=500";
    const refused = () =>
      filter(
        roleColumns({ min: "1000", max: "500" }, NONE, {
          max: { code: "VALUE_OUT_OF_RANGE", minimum: "1000" },
        }),
      );
    const { rerender } = render(refused());
    const headcount = screen.getByRole("textbox", { name: "Effectif, min." });
    await userEvent.type(headcount, "3");
    // A sort arrives meanwhile, the bounds as they were: neither the entry nor the focus moves.
    page.search = "role_monthly_hours_min=1000&role_monthly_hours_max=500&role_sort_by=label";
    rerender(refused());
    expect(headcount).toHaveValue("3");
    expect(headcount).toHaveFocus();
  });
});

describe("the refusals of the server on the bounds of a list", () => {
  it("says at its field a bound the server does not take for a number", () => {
    render(
      filter(roleColumns(NONE, { min: undefined, max: "3" }, { min: { code: "NUMBER_INVALID" } })),
    );
    const least = screen.getByRole("textbox", { name: "Heures par mois, min." });
    expect(least).toHaveAttribute("aria-invalid", "true");
    expect(least).toHaveAccessibleDescription("Ce n’est pas un nombre valide.");
    expect(least).toHaveFocus();
  });

  it("says at the choice of the year that the server requires it", () => {
    const scope: RangeScope = {
      name: "rate_year",
      label: "Année du taux",
      choices: [{ value: "2026", text: "2026" }],
      chosen: "2026",
      refused: { code: "VALUE_REQUIRED" },
    };
    render(
      filter([{ column: "rate", label: "Taux horaire", bounds: { min: "100", max: undefined } }], {
        scope,
      }),
    );
    const year = screen.getByRole("combobox", { name: "Année du taux" });
    expect(year).toHaveAttribute("aria-invalid", "true");
    expect(year).toHaveAccessibleDescription("Une valeur est requise.");
    expect(year).toHaveFocus();
  });

  it("bounds the depth of a tree by whole numbers from 1", async () => {
    render(filter([{ column: "org_level", label: "Niveau", bounds: NONE }], { kind: "level" }));
    const least = screen.getByRole("textbox", { name: "Niveau, min." });
    await userEvent.type(least, "1,5{Enter}");
    expect(router.push).not.toHaveBeenCalled();
    expect(least).toHaveAccessibleDescription("Ce n’est pas un nombre valide.");
    await userEvent.clear(least);
    await userEvent.type(least, "2{Enter}");
    expect(lastAddress()).toBe("/reference/resources?org_level_min=2");
  });
});
