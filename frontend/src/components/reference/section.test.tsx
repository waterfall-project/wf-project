// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of a section of the reference data (EP-25, US-2310/L2, #3446): a section with nothing to
 * list says it in one sentence in place of its body, its title kept. A server component, tried in
 * the node project.
 */
import { Bell } from "lucide-react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ReferenceCard } from "./section";

describe("ReferenceCard", () => {
  it("says an empty section in one sentence in place of its body, under its title [WF-IHM-0100-A]", () => {
    const html = renderToStaticMarkup(
      <ReferenceCard title="Alertes" icon={Bell} empty="Aucune alerte en cours.">
        <table />
      </ReferenceCard>,
    );
    expect(html).toContain('<section aria-label="Alertes" data-slot="section-card"');
    expect(html).toContain("Aucune alerte en cours.");
    expect(html).not.toContain("<table");
  });

  it("shows its body when the section has something to list [WF-IHM-0100-A]", () => {
    const html = renderToStaticMarkup(
      <ReferenceCard title="Alertes" icon={Bell}>
        <table />
      </ReferenceCard>,
    );
    expect(html).toContain("<table");
  });
});
