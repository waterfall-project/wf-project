// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CompletionDate } from "@/components/grid/completion-date";
import { CATALOGUES } from "@/i18n/catalogues";

import { TimeZoneProvider } from "./time-zone";

// The date a completion asks for is proposed in the time zone of the installation (WF-PLA-0130,
// WF-DAT-0100), whatever the zone of the workstation: at 23:30 universal time, Paris is on the
// next day.
function proposed(timeZone: string | undefined): string {
  render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <TimeZoneProvider timeZone={timeZone}>
        <CompletionDate onAnswer={vi.fn()} />
      </TimeZoneProvider>
    </NextIntlClientProvider>,
  );
  const field = screen.getByLabelText(CATALOGUES.en.remainingGrid.completionDate);
  return (field as HTMLInputElement).value;
}

describe("the day an installation proposes", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-13T23:30:00Z"));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("is the next day for an installation in Paris at 23:30 universal time [WF-PLA-0130-A]", () => {
    expect(proposed("Europe/Paris")).toBe("2026-11-14");
  });

  it("is the day of universal time for an installation in UTC [WF-PLA-0130-A]", () => {
    expect(proposed("UTC")).toBe("2026-11-13");
  });

  it("is the day of universal time when the installation is out of reach [WF-PLA-0130-A]", () => {
    expect(proposed(undefined)).toBe("2026-11-13");
  });
});
