// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { type AuditEvent, auditGrid } from "./audit-columns";

interface Journal {
  readonly items: readonly AuditEvent[];
}

const witness = (example("audit_events") as Journal).items;
const anonymised = (example("audit_events_anonymized_actor") as Journal).items;

/** The value the column of the authors reads of an inscription, the one its sort is offered by. */
function authorValue(event: AuditEvent) {
  const column = auditGrid({ openable: [], functions: [], revision: false }).columns.find(
    (each) => each.key === "actor",
  );
  return column?.value(event);
}

describe("the column of the authors of the journal", () => {
  it("orders an anonymised author after the names and before the platform, as the server sorts them [WF-IHM-0060-A]", () => {
    const named = witness.find((event) => typeof event.actor.display_name === "string");
    const platform = witness.find((event) => event.actor.kind === "platform");
    const nameless = anonymised[0];
    expect(named && platform && nameless).toBeTruthy();
    const events = [platform, nameless, named].filter((event) => event !== undefined);
    const sorted = [...events].sort((a, b) =>
      String(authorValue(a)) < String(authorValue(b)) ? -1 : 1,
    );
    expect(sorted.map((event) => event.actor)).toEqual([
      named?.actor,
      nameless?.actor,
      platform?.actor,
    ]);
  });
});
