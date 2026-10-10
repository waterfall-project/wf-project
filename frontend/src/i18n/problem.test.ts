// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import type { NodeList } from "@/components/grid/nodes";
import { example } from "@/test/fixtures";

import { CATALOGUES } from "./catalogues";
import type { Locale } from "./locale";
import { LINES_IN_SENTENCE, namedLines, problemMessage, type ProblemText } from "./problem";

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

  it("says the last administrator kept, by the condition her deactivation lacks, or by its own code for roles that would take her permissions away [WF-ADM-0120-A]", () => {
    const deactivation = example("user_deactivation_refused") as ProblemText;
    expect(say(deactivation, "fr")).toBe(
      "L\u2019état actuel ne permet pas cette opération. Condition non remplie\u00A0: un autre compte actif portant les permissions d\u2019administration.",
    );
    for (const name of ["user_access_roles_refused", "access_role_update_refused"]) {
      expect(say(example(name) as ProblemText, "fr")).toBe(
        "Au moins un compte actif doit garder les permissions d\u2019administration.",
      );
    }
  });

  it("names the state that forbids the operation by its label in the enumeration the refusal names, and the object it is the state of", () => {
    // The indicators of a project in pricing, and its workload on a reference it does not have:
    // the state of a project, said so (#413).
    for (const name of ["project_indicators_not_in_progress", "workload_no_reference"] as const) {
      const project = example(name) as ProblemText;
      expect(say(project, "fr")).toBe(
        "L\u2019état actuel ne permet pas cette opération. État du projet\u00A0: Chiffrage.",
      );
      expect(say(project, "en")).toBe(
        "The current state does not allow this operation. State of the project: Pricing.",
      );
    }
  });

  it("says no state whose enumeration the refusal does not name, nor a value its enumeration does not have", () => {
    const { params, ...refused } = example("project_indicators_not_in_progress") as ProblemText;
    const bare = "The current state does not allow this operation.";
    expect(say({ ...refused, params: { state: params?.state } }, "en")).toBe(bare);
    expect(say({ ...refused, params: { ...params, state: "occurred" } }, "en")).toBe(bare);
  });

  it("lists the missing prerequisites in the reader's language", () => {
    const problem: ProblemText = {
      code: "REFERENCE_INCOMPLETE",
      params: { missing_prerequisites: ["active_cost_category", "active_resource_role"] },
    };
    expect(say(problem, "fr")).toBe(
      "Le référentiel minimal est incomplet. À compléter\u00A0: une catégorie de main-d’œuvre active et un rôle de ressource actif.",
    );
    expect(say(problem, "en")).toBe(
      "The minimum reference data is incomplete. Still missing: an active labour category and an active resource role.",
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
      "The minimum reference data is incomplete. Still missing: a default calendar with working hours, an active labour category and an active resource role.",
    );
  });

  it("names the lines that bear a sub-project its deletion is refused for, by their numbers and their labels, in the reader's language [WF-DAT-0080-A]", () => {
    // La suppression d'un sous-projet que portent des lignes de devis de la révision en cours est
    // refusée et nomme ces lignes.
    const refused = example("subproject_delete_estimated") as ProblemText;
    expect(say(refused, "fr")).toBe(
      "L’état actuel ne permet pas cette opération. Condition non remplie\u00A0: aucune ligne de " +
        "devis de la révision en cours portant le sous-projet. Lignes de devis de la révision en " +
        "cours qui portent le sous-projet\u00A0: ligne 10 «\u00A0Raccordement des borniers\u00A0» " +
        "et ligne 11 «\u00A0Borniers\u00A0». Une ligne de provision change de sous-projet par son " +
        "risque.",
    );
    expect(say(refused, "en")).toBe(
      "The current state does not allow this operation. Unmet condition: no estimate line of the " +
        "current revision bearing the subproject. Estimate lines of the current revision that " +
        "bear the subproject: line 10 “Raccordement des borniers” and line 11 “Borniers”. A " +
        "provision line changes subproject through its risk.",
    );
  });

  it("names only the well-formed lines a refusal gives, and none of an empty list", () => {
    const { params, ...refused } = example("subproject_delete_estimated") as ProblemText;
    const given: unknown = params?.estimate_lines;
    const first: unknown = Array.isArray(given) ? given[0] : undefined;
    const condition =
      "The current state does not allow this operation. Unmet condition: no estimate line of the " +
      "current revision bearing the subproject.";
    // A line without its number as a number is left out, the other named.
    const mixed = { ...params, estimate_lines: [first, { row_number: "11", label: "Borniers" }] };
    expect(say({ ...refused, params: mixed }, "en")).toBe(
      `${condition} Estimate lines of the current revision that bear the subproject: line 10 ` +
        "“Raccordement des borniers”. A provision line changes subproject through its risk.",
    );
    expect(say({ ...refused, params: { ...params, estimate_lines: [] } }, "en")).toBe(condition);
  });

  it("counts the lines that bear a sub-project beyond a few, which the notice lists", () => {
    // A counterfactual variant of `subproject_delete_estimated`: the first six lines of the main
    // structure of the witness borne by the sub-project, the rest of the refusal kept.
    const refused = example("subproject_delete_estimated") as ProblemText;
    const volume = example("volume/nodes_thousand") as NodeList;
    const lines = volume.items
      .filter((node) => node.estimate_line !== undefined && node.estimate_line !== null)
      .slice(0, LINES_IN_SENTENCE + 1)
      .map(({ node_id, row_number, estimate_line }) => ({
        structure_id: "01926f3a-7c00-7000-8000-000000000201",
        node_id,
        row_number,
        label: estimate_line?.label ?? "",
      }));
    const listed = { ...refused, params: { ...refused.params, estimate_lines: lines } };
    expect(say(listed, "fr")).toMatch(
      /portant le sous-projet\. 6 lignes de devis de la révision en cours portent le sous-projet, listées ci-dessous\. Une ligne de provision change de sous-projet par son risque\.$/,
    );
    expect(namedLines(listed.params).map((line) => line.row_number)).toEqual(
      lines.map((line) => line.row_number),
    );
  });

  it("says how many columns a paste may have", () => {
    const problem: ProblemText = { code: "PASTE_TOO_WIDE", params: { max_columns: 12 } };
    expect(say(problem, "en")).toBe(
      "The pasted data has more columns than the grid. The grid accepts at most 12 columns from this cell.",
    );
    expect(say({ code: "PASTE_TOO_WIDE", params: { max_columns: 1 } }, "fr")).toBe(
      "Les données collées ont plus de colonnes que la grille. La grille accepte au plus 1 colonne à partir de cette cellule.",
    );
  });

  it("says the minimum a value falls short of", () => {
    // The retention of the copies outside the platform, at least that of the platform (#488).
    const problem: ProblemText = { code: "VALUE_OUT_OF_RANGE", params: { minimum: 7 } };
    expect(say(problem, "fr")).toBe(
      "La valeur sort des limites admises. Valeur minimale\u00A0: 7.",
    );
    expect(say(problem, "en")).toMatch(/ Minimum value: 7\.$/);
  });

  it("says the minimum of a refusal by field, with the refusal and at the field, written in the language of the reader", () => {
    // The retention of the copies outside the platform refused at its field (#293, #488), and a
    // rate under the smallest amount the service takes, an amount of the contract.
    const problem: ProblemText = {
      code: "VALIDATION_FAILED",
      fields: [
        { params: { minimum: 7 } },
        { params: { minimum: "1234.5" } },
        { params: { minimum: "not a number" } },
        {},
      ],
    };
    expect(say(problem, "fr")).toBe(
      "Les données saisies ne sont pas valides. Valeur minimale\u00A0: 7. Valeur minimale\u00A0: 1\u202F234,5.",
    );
    expect(say(problem, "en")).toBe(
      "The data entered is not valid. Minimum value: 7. Minimum value: 1,234.5.",
    );
    // A refusal by field is a code and its parameters: a form says it at the field so.
    const field = { code: "VALUE_OUT_OF_RANGE", params: { minimum: 7 } } as const;
    expect(say(field, "fr")).toBe("La valeur sort des limites admises. Valeur minimale\u00A0: 7.");
  });

  it("says the bound each field crosses, the largest as the smallest, written in the language of the reader", () => {
    // The two rates of a project, ratios from 0 to 1 (EP-14/L42i): the probability of winning
    // above the largest, the inflation rate under the smallest; a date bound is the period's to say.
    const problem: ProblemText = {
      code: "VALIDATION_FAILED",
      fields: [
        { params: { maximum: "1" } },
        { params: { minimum: "0" } },
        { params: { maximum: "0.75" } },
        { params: { maximum: "2026-06-03" } },
      ],
    };
    expect(say(problem, "fr")).toBe(
      "Les données saisies ne sont pas valides. Valeur maximale : 1. Valeur minimale : 0. Valeur maximale : 0,75.",
    );
    expect(say({ code: "VALUE_OUT_OF_RANGE", params: { maximum: 100 } }, "en")).toBe(
      "The value is outside the allowed range. Maximum value: 100.",
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

  it("names the format and the version a file was expected in [WF-INTF-0070-A]", () => {
    const problem = example("import_format_unreadable") as ProblemText;
    expect(say(problem, "fr")).toBe(
      "Le format du fichier est illisible. Format attendu\u00A0: Devis. Version attendue\u00A0: 1.",
    );
    expect(say(problem, "en")).toBe(
      "The file format cannot be read. Expected format: Estimate. Expected version: 1.",
    );
  });

  it("says nothing of what a reader cannot use, nor of a value it has no label for", () => {
    const problem: ProblemText = {
      code: "STATE_FORBIDS_OPERATION",
      params: {
        conflicting_object_id: "01926f3a-7c00-7000-8000-000000000501",
        missing_permission: "planning.delete",
        missing_condition: 12,
        missing_prerequisites: "active_cost_category",
        estimate_lines: [{ row_number: "10", label: "Borniers" }],
        max_columns: "12",
        component: "toString",
      },
    };
    expect(say(problem, "en")).toBe("The current state does not allow this operation.");
    // A lock version, the one parameter of a refusal of a stale version, names nothing either.
    const stale = { code: "STALE_LOCK_VERSION", params: { expected_lock_version: 4 } } as const;
    expect(say(stale, "en")).toBe(
      "Someone changed this data in the meantime; reload it to see its latest version.",
    );
    const unlabelled = { missing_prerequisites: ["constructor", "__proto__"] };
    expect(say({ code: "REFERENCE_INCOMPLETE", params: unlabelled }, "en")).toBe(
      "The minimum reference data is incomplete.",
    );
  });
});
