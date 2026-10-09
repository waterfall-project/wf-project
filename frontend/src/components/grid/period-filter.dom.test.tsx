// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";

import { PendingAddress } from "./pending-address";
import type { Period, PeriodKind, PeriodRefusals } from "./period";
import { PeriodFilter } from "./period-filter";

// The server of Next, as far as the filter needs it: the address it reads and the navigations it
// asks.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const NONE: Period = { from: undefined, to: undefined };

/** A filter of a period, in French, sharing the address last asked as the page does. */
function filter(
  period: Period = NONE,
  refused?: PeriodRefusals,
  kind: PeriodKind = "date",
): ReactNode {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <PeriodFilter
          label="Période de modification"
          kind={kind}
          period={period}
          refused={refused}
          page="offset"
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The address of the last navigation the filter asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

/** The field of a side of the period. */
function field(side: "Du" | "Au"): HTMLElement {
  return screen.getByLabelText(side);
}

/** Enter a day in a field of a date, as the browser gives it: the whole value at once. */
function enter(side: "Du" | "Au", day: string) {
  fireEvent.change(field(side), { target: { value: day } });
}

/** A period whose end the server refused for preceding its start. */
function inverted(from: string, to: string): ReactNode {
  return filter({ from, to }, { to: { code: "VALUE_OUT_OF_RANGE", minimum: from } });
}

beforeEach(() => {
  page.search = "";
});

afterEach(() => {
  router.push.mockClear();
});

describe("the filter of a list on a period of days of planning", () => {
  it("writes both days entered under the names of the contract, back to the first page, the rest kept", async () => {
    page.search = "sort_by=code&offset=50&to=2026-04-30";
    render(filter({ from: undefined, to: "2026-04-30" }));
    const form = screen.getByRole("form", { name: "Période de modification" });
    expect(field("Au")).toHaveValue("2026-04-30");
    enter("Du", "2026-03-01");
    // Each side keeps the other: a start after the end is not offered.
    expect(field("Du")).toHaveAttribute("max", "2026-04-30");
    expect(field("Au")).toHaveAttribute("min", "2026-03-01");
    await userEvent.click(within(form).getByRole("button", { name: "Filtrer" }));
    expect(lastAddress()).toBe("/?sort_by=code&to=2026-04-30&from=2026-03-01");
  });

  it("lifts a side emptied", async () => {
    page.search = "from=2026-03-01&to=2026-03-16";
    render(filter({ from: "2026-03-01", to: "2026-03-16" }));
    enter("Au", "");
    await userEvent.click(screen.getByRole("button", { name: "Filtrer" }));
    expect(lastAddress()).toBe("/?from=2026-03-01");
  });

  it("says at its field the end the server refused for preceding the start it names, which takes the focus, and breaks no rule of accessibility", async () => {
    page.search = "from=2026-03-31&to=2026-03-01";
    const { container } = render(inverted("2026-03-31", "2026-03-01"));
    expect(field("Au")).toHaveAttribute("aria-invalid", "true");
    expect(field("Au")).toHaveFocus();
    expect(field("Au")).toHaveAccessibleDescription(
      "La fin de la période ne peut précéder son début, 31 mars 2026.",
    );
    expect(field("Du")).not.toHaveAttribute("aria-invalid");
    await expectAccessible(container);
  });

  it("says at its field a day the server does not take", () => {
    render(filter({ from: "2026-03-01", to: undefined }, { from: { code: "DATE_INVALID" } }));
    expect(field("Du")).toHaveAttribute("aria-invalid", "true");
    expect(field("Du")).toHaveAccessibleDescription("Ce n’est pas une date valide.");
  });

  it("gives the focus to the end refused each time the list comes back refused, the same side refused again", () => {
    page.search = "from=2026-03-31&to=2026-03-01";
    const { rerender } = render(inverted("2026-03-31", "2026-03-01"));
    expect(field("Au")).toHaveFocus();
    // The focus elsewhere, another inverted period reached in the history comes back refused on
    // the same side: its field takes the focus anew.
    screen.getByRole("button", { name: "Filtrer" }).focus();
    page.search = "from=2026-03-31&to=2026-03-02";
    rerender(inverted("2026-03-31", "2026-03-02"));
    expect(field("Au")).toHaveFocus();
    expect(field("Au")).toHaveValue("2026-03-02");
  });

  it("keeps the focus on the button that sent the period once the address arrives, the form never remounted", async () => {
    const { rerender } = render(filter());
    enter("Du", "2026-03-01");
    const apply = screen.getByRole("button", { name: "Filtrer" });
    await userEvent.click(apply);
    page.search = "from=2026-03-01";
    rerender(filter({ from: "2026-03-01", to: undefined }));
    expect(screen.getByRole("button", { name: "Filtrer" })).toBe(apply);
    expect(apply).toHaveFocus();
    expect(field("Du")).toHaveValue("2026-03-01");
  });

  it("shows the period of the address anew when it changes back in the history, what was entered and not sent given up", () => {
    page.search = "from=2026-03-01";
    const { rerender } = render(filter({ from: "2026-03-01", to: undefined }));
    enter("Au", "2026-03-20");
    page.search = "from=2026-02-01";
    rerender(filter({ from: "2026-02-01", to: undefined }));
    expect(field("Du")).toHaveValue("2026-02-01");
    page.search = "from=2026-03-01";
    rerender(filter({ from: "2026-03-01", to: undefined }));
    expect(field("Du")).toHaveValue("2026-03-01");
    expect(field("Au")).toHaveValue("");
  });

  it("keeps what is entered through a change of the address the form does not write", () => {
    page.search = "from=2026-03-01";
    const { rerender } = render(filter({ from: "2026-03-01", to: undefined }));
    enter("Au", "2026-03-20");
    page.search = "from=2026-03-01&sort_by=code";
    rerender(filter({ from: "2026-03-01", to: undefined }));
    expect(field("Au")).toHaveValue("2026-03-20");
  });
});

describe("the filter of a list on a period of local days, sent as instants", () => {
  const original = process.env.TZ;

  beforeEach(() => {
    process.env.TZ = "Europe/Paris";
  });

  afterEach(() => {
    process.env.TZ = original;
  });

  it("sends the start of the first day and the start of the day after the last, in universal time, back to the first page", async () => {
    page.search = "sort_by=code&offset=50";
    render(filter(NONE, undefined, "day"));
    enter("Du", "2026-03-01");
    enter("Au", "2026-03-31");
    await userEvent.click(screen.getByRole("button", { name: "Filtrer" }));
    expect(lastAddress()).toBe(
      "/?sort_by=code&from=2026-02-28T23%3A00%3A00.000Z&to=2026-03-31T22%3A00%3A00.000Z",
    );
  });

  it("shows the local days of the instants of the address, a bound left untouched sent as the address names it", async () => {
    page.search = "from=2026-02-28T23%3A00%3A00Z&to=2026-03-31T22%3A00%3A00Z";
    render(filter({ from: "2026-02-28T23:00:00Z", to: "2026-03-31T22:00:00Z" }, undefined, "day"));
    expect(field("Du")).toHaveValue("2026-03-01");
    expect(field("Au")).toHaveValue("2026-03-31");
    expect(field("Au")).toHaveAttribute("min", "2026-03-01");
    enter("Du", "2026-03-10");
    await userEvent.click(screen.getByRole("button", { name: "Filtrer" }));
    expect(lastAddress()).toBe("/?from=2026-03-09T23%3A00%3A00.000Z&to=2026-03-31T22%3A00%3A00Z");
  });

  it("says at its field the end the server refused, by the local day of the start it names", () => {
    page.search = "from=2026-03-31T22%3A00%3A00Z&to=2026-02-28T23%3A00%3A00Z";
    render(
      filter(
        { from: "2026-03-31T22:00:00Z", to: "2026-02-28T23:00:00Z" },
        { to: { code: "VALUE_OUT_OF_RANGE", minimum: "2026-03-31T22:00:00Z" } },
        "day",
      ),
    );
    expect(field("Au")).toHaveFocus();
    expect(field("Au")).toHaveAccessibleDescription(
      "La fin de la période ne peut précéder son début, 1 avr. 2026.",
    );
  });
});

describe("the filter of a list on a period of instants", () => {
  const original = process.env.TZ;

  beforeEach(() => {
    process.env.TZ = "Europe/Paris";
  });

  afterEach(() => {
    process.env.TZ = original;
  });

  it("says at its field the end the server refused, by the start it names in the local time", () => {
    render(
      filter(
        { from: "2026-06-03T14:00:00Z", to: "2026-06-01T00:00:00Z" },
        { to: { code: "VALUE_OUT_OF_RANGE", minimum: "2026-06-03T14:00:00Z" } },
        "instant",
      ),
    );
    expect(field("Du")).toHaveValue("2026-06-03T16:00");
    expect(field("Au")).toHaveAttribute("aria-invalid", "true");
    expect(field("Au")).toHaveAccessibleDescription(
      /^La fin de la période ne peut précéder son début, 3 juin 2026.*16:00\.$/,
    );
  });
});
