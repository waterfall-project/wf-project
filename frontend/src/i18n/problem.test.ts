// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";

import { CATALOGUES } from "./catalogues";
import type { Locale } from "./locale";
import { problemMessage, type ProblemText } from "./problem";

type ErrorCode = components["schemas"]["ErrorCode"];

/** The sentence of a refusal in a language. */
function say(problem: ProblemText, locale: Locale): string {
  return problemMessage(problem, { locale, messages: CATALOGUES[locale] });
}

describe("the sentence of a refusal", () => {
  it("is written by the catalogue of the reader's language, from the code alone", () => {
    expect(say({ code: "NOT_FOUND" }, "fr")).toBe(
      "Introuvable\u00A0: cet élément n\u2019existe pas, ou vous n\u2019y avez pas accès.",
    );
    expect(say({ code: "NOT_FOUND" }, "en")).toBe(
      "Not found: this item does not exist, or you do not have access to it.",
    );
  });

  it("has a sentence for every code of the contract, in both languages", () => {
    for (const locale of ["fr", "en"] as const) {
      const errors: Readonly<Record<ErrorCode, string>> = CATALOGUES[locale].errors;
      for (const [code, text] of Object.entries(errors)) {
        expect(text, `${locale} ${code}`).toMatch(/\.$/);
      }
    }
  });

  it("names the missing permission by its label", () => {
    const problem: ProblemText = {
      code: "PERMISSION_MISSING",
      params: { missing_permission: "planning.write" },
    };
    expect(say(problem, "fr")).toBe(
      "Vous n\u2019avez pas la permission nécessaire. Permission requise\u00A0: Modifier la planification.",
    );
    expect(say(problem, "en")).toBe(
      "You do not have the required permission. Required permission: Edit planning.",
    );
  });

  it("names a permission of its own, without a function", () => {
    const problem: ProblemText = {
      code: "PERMISSION_MISSING",
      params: { missing_permission: "revision_mark" },
    };
    expect(say(problem, "en")).toBe(
      "You do not have the required permission. Required permission: Mark a revision.",
    );
  });

  it("names the missing condition by its label", () => {
    const problem: ProblemText = {
      code: "STATE_FORBIDS_OPERATION",
      params: { missing_condition: "revision_draft" },
    };
    expect(say(problem, "fr")).toBe(
      "L\u2019état actuel ne permet pas cette opération. Condition non remplie\u00A0: révision en cours d\u2019élaboration.",
    );
    expect(say(problem, "en")).toBe(
      "The current state does not allow this operation. Unmet condition: draft revision.",
    );
  });

  it("lists the missing prerequisites in the reader's language", () => {
    const problem: ProblemText = {
      code: "REFERENCE_INCOMPLETE",
      params: { missing_prerequisites: ["active_cost_category", "active_resource_role"] },
    };
    expect(say(problem, "fr")).toBe(
      "Le référentiel minimal est incomplet. À compléter\u00A0: une catégorie de coût active et un rôle de ressource actif.",
    );
    expect(say(problem, "en")).toBe(
      "The minimum reference data is incomplete. Still missing: an active cost category and an active resource role.",
    );
  });

  it("lists three prerequisites as British English does, without a serial comma", () => {
    const problem: ProblemText = {
      code: "REFERENCE_INCOMPLETE",
      params: {
        missing_prerequisites: [
          "default_calendar_with_hours",
          "active_cost_category",
          "active_resource_role",
        ],
      },
    };
    expect(say(problem, "en")).toBe(
      "The minimum reference data is incomplete. Still missing: a default calendar with working hours, an active cost category and an active resource role.",
    );
  });

  it("says how many columns a paste may have", () => {
    const problem: ProblemText = { code: "PASTE_TOO_WIDE", params: { max_columns: 12 } };
    expect(say(problem, "en")).toBe(
      "The pasted data has more columns than the grid. The grid accepts at most 12 columns.",
    );
    expect(say({ code: "PASTE_TOO_WIDE", params: { max_columns: 1 } }, "fr")).toBe(
      "Les données collées ont plus de colonnes que la grille. La grille accepte au plus 1 colonne.",
    );
  });

  it("names the unavailable component", () => {
    const problem: ProblemText = {
      code: "COMPONENT_UNAVAILABLE",
      params: { component: "database" },
    };
    expect(say(problem, "fr")).toBe(
      "Un composant du service est indisponible. Composant indisponible\u00A0: Base de données.",
    );
  });

  it("says nothing of what a reader cannot use, nor of a value it has no label for", () => {
    const problem: ProblemText = {
      code: "STALE_LOCK_VERSION",
      params: {
        conflicting_object_id: "01926f3a-7c00-7000-8000-000000000501",
        expected_lock_version: 4,
        missing_permission: "planning.delete",
        missing_condition: 12,
        missing_prerequisites: "active_cost_category",
        max_columns: "12",
        component: "toString",
      },
    };
    expect(say(problem, "en")).toBe(
      "Someone changed this data in the meantime; reload it to see its latest version.",
    );
    const unlabelled = { missing_prerequisites: ["constructor", "__proto__"] };
    expect(say({ code: "REFERENCE_INCOMPLETE", params: unlabelled }, "en")).toBe(
      "The minimum reference data is incomplete.",
    );
  });
});
