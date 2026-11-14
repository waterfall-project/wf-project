// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { today } from "./address";

// The current day is the day of the time zone of the installation, never the workstation's nor
// universal time (WF-PLA-0130, WF-DAT-0100); the instant is fixed, the machine's zone plays no part.
describe("today", () => {
  const lateEvening = new Date("2026-11-13T23:30:00Z");

  it("proposes the next day to an installation in Paris at 23:30 universal time [WF-PLA-0130-A]", () => {
    expect(today("Europe/Paris", lateEvening)).toBe("2026-11-14");
  });

  it("keeps the same day in universal time [WF-PLA-0130-A]", () => {
    expect(today("UTC", lateEvening)).toBe("2026-11-13");
  });

  it("gives the same day to a zone west of Greenwich [WF-PLA-0130-A]", () => {
    expect(today("America/New_York", lateEvening)).toBe("2026-11-13");
  });

  it("gives the day before to a zone far enough west, shortly after midnight universal time [WF-PLA-0130-A]", () => {
    expect(today("America/Los_Angeles", new Date("2026-11-14T00:30:00Z"))).toBe("2026-11-13");
  });

  it("pads the month and the day [WF-PLA-0130-A]", () => {
    expect(today("Asia/Tokyo", new Date("2026-03-01T00:00:00Z"))).toBe("2026-03-01");
  });
});
