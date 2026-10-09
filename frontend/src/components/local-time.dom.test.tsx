// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import type { Locale } from "@/i18n/locale";

import { LocalTime } from "./local-time";

const INSTANT = "2026-06-30T23:30:00Z";

/** An instant, in a page of a language. */
function page(locale: Locale) {
  return (
    <NextIntlClientProvider locale={locale}>
      <LocalTime value={INSTANT} />
    </NextIntlClientProvider>
  );
}

describe("an instant", () => {
  const original = process.env.TZ;

  afterEach(() => {
    process.env.TZ = original;
  });

  it("shows in the local time of the workstation, in the language of the page", () => {
    process.env.TZ = "America/Los_Angeles";
    render(page("fr"));
    const time = screen.getByText("30 juin 2026, 16:30");
    expect(time.tagName).toBe("TIME");
    expect(time).toHaveAttribute("datetime", INSTANT);
  });

  it("moves with the time zone of the workstation", () => {
    process.env.TZ = "Asia/Tokyo";
    render(page("fr"));
    expect(screen.getByText("1 juil. 2026, 08:30")).toBeInTheDocument();
  });

  it("is left to the browser by the server, which knows only its own zone", () => {
    expect(renderToString(page("en"))).toBe(`<time dateTime="${INSTANT}"></time>`);
  });
});
