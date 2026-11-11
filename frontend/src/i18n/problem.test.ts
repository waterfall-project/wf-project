// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";
import { fromExample, say } from "@/test/refusals";

import { CATALOGUES } from "./catalogues";
import { problemMessage, type ProblemText } from "./problem";

type ErrorCode = components["schemas"]["ErrorCode"];

/**
 * Every column of an extraction of actual costs the contract names: typed by the enumeration, so
 * that a column added to it fails the type check here until the catalogue is told.
 */
const SOURCE_COLUMNS: Record<components["schemas"]["ActualCostSourceColumn"], true> = {
  wbs_element: true,
  document_number: true,
  document_item: true,
  document_date: true,
  amount: true,
};

/**
 * The refusal of an import of actual costs whose mapping lacks labels
 * (`import_actual_cost_mapping_incomplete`).
 */
const MAPPING_INCOMPLETE: ProblemText = {
  code: "STATE_FORBIDS_OPERATION",
  params: {
    missing_condition: "actual_cost_mapping_complete",
    columns: ["wbs_element", "document_number", "document_date", "amount"],
  },
};

/** A refusal for the state of a project in pricing (`project_indicators_not_in_progress`). */
const PROJECT_IN_PRICING: ProblemText = {
  code: "STATE_FORBIDS_OPERATION",
  params: { state: "pricing", state_enum: "ProjectState" },
};

/** The refusal of the start of a task on a Saturday (`task_date_non_working_day`). */
const TASK_ON_SATURDAY: ProblemText = {
  code: "VALIDATION_FAILED",
  fields: [
    {
      pointer: "/start/date",
      code: "NON_WORKING_DAY",
      params: { date: "2026-12-19", next_working_day: "2026-12-21" },
    },
  ],
};

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

  it.each([
    [
      "session_revoked",
      "SESSION_REVOKED",
      "fr",
      "Votre session a été fermée — déconnexion, désactivation du compte ou retrait de ses rôles\u202F; reconnectez-vous en saisissant à nouveau vos identifiants.",
    ],
    [
      "session_revoked",
      "SESSION_REVOKED",
      "en",
      "Your session has been closed — by a sign-out, the deactivation of the account or the withdrawal of its roles; sign in again with your credentials.",
    ],
    ["session_expired", "SESSION_EXPIRED", "fr", "Votre session a expiré\u202F; reconnectez-vous."],
    ["session_expired", "SESSION_EXPIRED", "en", "Your session has expired; please sign in again."],
  ] as const)(
    "says a session closed — whose sign-in asks for the identifiers again — apart from one expired (#855): %s, %s",
    (name, code, locale, sentence) => {
      // The example is read by what the sentence takes of it: its code, nothing else.
      expect(example(name)).toMatchObject({ code });
      expect(say({ code }, locale)).toBe(sentence);
    },
  );

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
      params: { missing_condition: "no_current_revision" },
    };
    const condition = CATALOGUES.fr.enums.CommandCondition.no_current_revision;
    expect(say(problem, "fr")).toBe(
      `L\u2019état actuel ne permet pas cette opération. Condition non remplie\u00A0: ${condition}.`,
    );
  });

  it("says a project terminal and a revision marked as facts, not as conditions unmet, from the refusals of the contract (US-0702/L1)", () => {
    // The examples are read by what the sentences take of them: if one changes, the assertion fails.
    expect(example("timeline_create_terminal")).toMatchObject({
      code: "STATE_FORBIDS_OPERATION",
      params: { missing_condition: "project_not_terminal" },
    });
    expect(example("node_create_marked_refused")).toMatchObject({
      code: "STATE_FORBIDS_OPERATION",
      params: { missing_condition: "revision_draft" },
    });
    const terminal: ProblemText = {
      code: "STATE_FORBIDS_OPERATION",
      params: { missing_condition: "project_not_terminal" },
    };
    const marked: ProblemText = {
      code: "STATE_FORBIDS_OPERATION",
      params: { missing_condition: "revision_draft" },
    };
    expect(say(terminal, "fr")).toBe(
      "L\u2019état actuel ne permet pas cette opération. Le projet est clos\u00A0: il ne se modifie plus.",
    );
    expect(say(marked, "fr")).toBe(
      "L\u2019état actuel ne permet pas cette opération. La révision est marquée\u00A0: elle ne se modifie plus.",
    );
    expect(say(marked, "en")).toBe(
      "The current state does not allow this operation. The revision is marked: it no longer changes.",
    );
  });

  it("names the object a later change took back, which an undo or a redo would undo, by the label the refusal gives [WF-IHM-0110-A]", () => {
    const later: ProblemText = {
      code: "UNDO_CONFLICT",
      params: {
        conflicting_object_id: "01926f3a-7c00-7000-8000-000000000553",
        conflicting_object_label: "Raccordement des borniers",
      },
    };
    for (const refused of ["undo_later_change", "redo_later_change"]) {
      expect(example(refused)).toMatchObject(later);
      expect(say(later, "fr")).toBe(
        `${CATALOGUES.fr.errors.UNDO_CONFLICT} Objet repris depuis\u00A0: «\u00A0Raccordement des borniers\u00A0».`,
      );
    }
    expect(say(later, "en")).toBe(
      `${CATALOGUES.en.errors.UNDO_CONFLICT} Object changed since: “Raccordement des borniers”.`,
    );
  });

  it("lists the categories of labour without an hourly rate for the year of reference, by their labels and the year [WF-DEV-0010-A]", () => {
    const missing = fromExample("estimate_line_rate_missing", {
      code: "HOURLY_RATE_MISSING",
      params: {
        missing_rates: [
          {
            cost_category_id: "01926f3a-7c00-7000-8000-000000000402",
            label: "Ingénierie électrique",
            year: 2026,
          },
        ],
      },
    });
    expect(say(missing, "fr")).toBe(
      `${CATALOGUES.fr.errors.HOURLY_RATE_MISSING} Sans taux horaire\u00A0: «\u00A0Ingénierie électrique\u00A0» en 2026.`,
    );
    expect(say(missing, "en")).toBe(
      `${CATALOGUES.en.errors.HOURLY_RATE_MISSING} Without an hourly rate: “Ingénierie électrique” in 2026.`,
    );
  });

  it("names the subordinates a summary task takes a date from, as the screen read them, and counts them otherwise [WF-IHM-0030-A]", () => {
    // A refusal by field is said at its field, by the sentence of the field's code and parameters.
    const ids = [
      "01926f3a-7c00-7000-8000-000000000552",
      "01926f3a-7c00-7000-8000-000000000556",
      "01926f3a-7c00-7000-8000-000000000541",
    ];
    expect(example("task_summary_date_refused")).toMatchObject({
      fields: [{ code: "SUMMARY_TASK_DERIVED", params: { subordinate_node_ids: ids } }],
    });
    const refused: ProblemText = {
      code: "SUMMARY_TASK_DERIVED",
      params: { subordinate_node_ids: ids },
    };
    const labels = ["Câblage des armoires", "Raccordement des borniers", "Essais"];
    const named = problemMessage(refused, {
      locale: "fr",
      messages: CATALOGUES.fr,
      names: Object.fromEntries(ids.map((id, rank) => [id, labels[rank] ?? ""])),
    });
    expect(named).toBe(
      `${CATALOGUES.fr.errors.SUMMARY_TASK_DERIVED} ` +
        "Elle tient cette valeur de ses subordonnées\u00A0: «\u00A0Câblage des armoires\u00A0», " +
        "«\u00A0Raccordement des borniers\u00A0» et «\u00A0Essais\u00A0».",
    );
    const progress = fromExample("task_progress_summary_refused", {
      code: "SUMMARY_TASK_DERIVED",
      params: {
        subordinate_node_ids: [
          "01926f3a-7c00-7000-8000-000000000522",
          "01926f3a-7c00-7000-8000-000000000523",
          "01926f3a-7c00-7000-8000-000000000524",
          "01926f3a-7c00-7000-8000-000000000525",
          "01926f3a-7c00-7000-8000-000000000526",
        ],
      },
    });
    expect(say(progress, "fr")).toBe(
      `${CATALOGUES.fr.errors.SUMMARY_TASK_DERIVED} Elle tient cette valeur de ses 5 subordonnées.`,
    );
  });

  it("names the risks whose line of provision a deletion would leave without a task, by their labels", () => {
    const refused = fromExample("node_delete_last_provision_task_refused", {
      code: "STATE_FORBIDS_OPERATION",
      params: {
        missing_condition: "at_least_one_task",
        risks: [
          {
            risk_id: "01926f3a-7c00-7000-8000-000000000751",
            label: "Risque de reprise du câblage",
          },
        ],
      },
    });
    expect(say(refused, "fr")).toBe(
      `L\u2019état actuel ne permet pas cette opération. Condition non remplie\u00A0: ${CATALOGUES.fr.enums.CommandCondition.at_least_one_task}. ` +
        "Risque concerné\u00A0: «\u00A0Risque de reprise du câblage\u00A0».",
    );
  });

  it("tells the refusals US-0702/L2 gave a code by their sentence: a predecessor named twice, a timeline of another project, a confirmation absent, an unexpected error", () => {
    for (const [refused, code] of [
      ["predecessors_duplicate", "DUPLICATE_PREDECESSOR"],
      ["node_tracking_timeline_unknown", "UNKNOWN_TIMELINE"],
    ] as const) {
      // Said at the field the refusal points at, by the sentence of the field's code alone.
      expect(example(refused)).toMatchObject({ fields: [{ code }] });
      expect(say({ code }, "fr")).toBe(CATALOGUES.fr.errors[code]);
    }
    for (const [refused, code] of [
      ["project_exit_unconfirmed", "CONFIRMATION_REQUIRED"],
      ["internal_error", "INTERNAL_ERROR"],
    ] as const) {
      expect(say(fromExample(refused, { code }), "fr")).toBe(CATALOGUES.fr.errors[code]);
    }
  });

  it("names the columns of the correspondence without a label, and the columns a file lacks with the labels declared for them [WF-REF-0190-A]", () => {
    const refused = fromExample("import_actual_cost_mapping_incomplete", MAPPING_INCOMPLETE);
    expect(say(refused, "en")).toBe(
      "The current state does not allow this operation. Unmet condition: actual-cost extraction mapping complete. Required columns without a label: WBS element, Document no., Document date, Amount.",
    );
    const missing = fromExample("import_actual_costs_column_missing", {
      code: "FILE_FORMAT_UNREADABLE",
      params: {
        expected_format: "actual_costs",
        missing_columns: [{ column: "amount", labels: ["Val./Devise objet"] }],
      },
    });
    expect(say(missing, "en")).toContain(
      "Required column missing from the file: Amount (declared label: \u201CVal./Devise objet\u201D).",
    );
    expect(say(missing, "fr")).toContain(
      "Colonne exigée absente du fichier\u00A0: Montant (intitulé déclaré\u00A0: \u00AB\u00A0Val./Devise objet\u00A0\u00BB).",
    );
  });

  it("labels every column of the contract in both catalogues, so that none is dropped from a refusal unheard [WF-REF-0190-A]", () => {
    const columns = Object.keys(SOURCE_COLUMNS).sort();
    for (const locale of ["en", "fr"] as const) {
      const catalogue = CATALOGUES[locale] as unknown as {
        enums: { ActualCostSourceColumn: Record<string, string> };
      };
      expect(Object.keys(catalogue.enums.ActualCostSourceColumn).sort()).toEqual(columns);
    }
  });

  it("names no columns of a refusal that is not the mapping incomplete, whatever its parameters [WF-REF-0190-A]", () => {
    const refused = fromExample("import_actual_cost_mapping_incomplete", MAPPING_INCOMPLETE);
    const other: ProblemText = {
      ...refused,
      params: { ...refused.params, missing_condition: "may_create_revision" },
    };
    expect(say(other, "en")).not.toContain("without a label");
  });

  it("says the last administrator kept, by the condition her deactivation lacks, or by its own code for roles that would take her permissions away [WF-ADM-0120-A]", () => {
    const deactivation = fromExample("user_deactivation_refused", {
      code: "STATE_FORBIDS_OPERATION",
      params: { missing_condition: "last_administrator" },
    });
    expect(say(deactivation, "fr")).toBe(
      "L\u2019état actuel ne permet pas cette opération. Condition non remplie\u00A0: un autre compte actif portant les permissions d\u2019administration.",
    );
    for (const name of ["user_access_roles_refused", "access_role_update_refused"]) {
      expect(say(fromExample(name, { code: "LAST_ADMINISTRATOR" }), "fr")).toBe(
        "Au moins un compte actif doit garder les permissions d\u2019administration.",
      );
    }
  });

  it("names the state that forbids the operation by its label in the enumeration the refusal names, and the object it is the state of", () => {
    // The indicators of a project in pricing, and its workload on a reference it does not have:
    // the state of a project, said so (#413).
    for (const name of ["project_indicators_not_in_progress", "workload_no_reference"] as const) {
      const project = fromExample(name, PROJECT_IN_PRICING);
      expect(say(project, "fr")).toBe(
        "L\u2019état actuel ne permet pas cette opération. État du projet\u00A0: Chiffrage.",
      );
      expect(say(project, "en")).toBe(
        "The current state does not allow this operation. State of the project: Pricing.",
      );
    }
  });

  it("says no state whose enumeration the refusal does not name, nor a value its enumeration does not have, nor an enumeration named after a property every object inherits (#413)", () => {
    const { params, ...refused } = fromExample(
      "project_indicators_not_in_progress",
      PROJECT_IN_PRICING,
    );
    const bare = "The current state does not allow this operation.";
    expect(say({ ...refused, params: { state: params?.state } }, "en")).toBe(bare);
    expect(say({ ...refused, params: { ...params, state: "occurred" } }, "en")).toBe(bare);
    for (const state_enum of ["toString", "__proto__"]) {
      const forged = { ...params, state_enum } as NonNullable<ProblemText["params"]>;
      expect(say({ ...refused, params: forged }, "en")).toBe(bare);
    }
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

  it("names the sub-project a line of a started task does not leave, which received actual costs, from the refusal of its field (#1066)", () => {
    const refused = fromExample("estimate_line_subproject_has_actual_costs", {
      code: "VALIDATION_FAILED",
      fields: [
        {
          pointer: "/subproject_id",
          code: "SUBPROJECT_HAS_ACTUAL_COSTS",
          params: {
            subproject: {
              subproject_id: "01926f3a-7c00-7000-8000-000000000801",
              label: "Poste de commande",
            },
          },
        },
      ],
    });
    expect(say(refused, "fr")).toBe(
      "Les données saisies ne sont pas valides. Sous-projet qui a reçu des coûts réels, que la " +
        "ligne ne quitte pas\u00A0: «\u00A0Poste de commande\u00A0».",
    );
    expect(say(refused, "en")).toBe(
      "The data entered is not valid. Subproject that has received actual costs, which the line " +
        "does not leave: “Poste de commande”.",
    );
    // The refusal of the field, said at the field, by its own code and the same sub-project.
    expect(refused.fields?.[0]?.params).toBeDefined();
    const params = refused.fields?.[0]?.params ?? {};
    expect(say({ code: "SUBPROJECT_HAS_ACTUAL_COSTS", params }, "fr")).toBe(
      "Cette ligne ne peut pas quitter ce sous-projet\u00A0: sa tâche est démarrée, et le " +
        "sous-projet a reçu des coûts réels. Sous-projet qui a reçu des coûts réels, que la ligne " +
        "ne quitte pas\u00A0: «\u00A0Poste de commande\u00A0».",
    );
  });

  it("names the cause of a line of a file rejected as the file bears it: the value no object has, the label two tasks share, the element of work breakdown, the rank of the duplicate [WF-INTF-0080-A] [WF-INTF-0120-A] [WF-CRE-0020-A]", () => {
    /** The rejections of an example of an import, as the test reads them, in their order. */
    const REJECTED: Readonly<Record<string, readonly ProblemText[]>> = {
      import_analysed: [
        { code: "UNKNOWN_TASK", params: { value: "Essais de compatibilité électromagnétique" } },
        { code: "UNKNOWN_RESOURCE_ROLE", params: { value: "Soudeur (SOUD)" } },
      ],
      import_actual_costs_wbs_invalid: [
        { code: "WBS_ELEMENT_INVALID", params: { wbs_element: "/SP-CAB" } },
      ],
      import_remaining_ambiguous_label: [
        {
          code: "AMBIGUOUS_TASK_LABEL",
          params: {
            label: "Mise en service",
            tasks: [
              { lineage_id: "01926f3a-7c00-7000-8000-000000000665", label: "Mise en service" },
              { lineage_id: "01926f3a-7c00-7000-8000-000200004672", label: "Mise en service" },
            ],
          },
        },
      ],
      import_actual_costs_duplicate_line: [
        { code: "DUPLICATE_COST_LINE", params: { rows: [5] } },
        { code: "DUPLICATE_COST_LINE", params: { rows: [4] } },
      ],
    };
    /** The nth rejection of an example of an import, which the example must carry. */
    const rejection = (name: string, index = 0): ProblemText => {
      const rejected = REJECTED[name] ?? [];
      expect(example(name)).toMatchObject({ report: { rejected } });
      const at = rejected.at(index);
      if (at === undefined) {
        throw new Error(`${name} has no rejection ${String(index)}`);
      }
      return at;
    };
    expect(say(rejection("import_analysed", 0), "fr")).toContain(
      "Valeur lue dans le fichier\u00A0: «\u00A0Essais de compatibilité électromagnétique\u00A0».",
    );
    expect(say(rejection("import_analysed", 1), "en")).toContain(
      "Value read in the file: “Soudeur (SOUD)”.",
    );
    expect(say(rejection("import_actual_costs_wbs_invalid"), "fr")).toContain(
      "Élément d’OTP lu\u00A0: «\u00A0/SP-CAB\u00A0».",
    );
    expect(say(rejection("import_actual_costs_wbs_invalid"), "en")).toContain(
      "Work breakdown element read: “/SP-CAB”.",
    );
    expect(say(rejection("import_remaining_ambiguous_label"), "fr")).toContain(
      "Libellé lu\u00A0: «\u00A0Mise en service\u00A0», porté par les tâches «\u00A0Mise en service\u00A0» et «\u00A0Mise en service\u00A0».",
    );
    expect(say(rejection("import_remaining_ambiguous_label"), "en")).toContain(
      "Label read: “Mise en service”, shared by the tasks “Mise en service” and “Mise en service”.",
    );
    expect(say(rejection("import_actual_costs_duplicate_line", 0), "fr")).toContain(
      "Autre ligne du fichier de même pièce et de même poste\u00A0: 5.",
    );
    expect(say(rejection("import_actual_costs_duplicate_line", 1), "en")).toContain(
      "Other line of the file with the same document and item: 4.",
    );
    // The code of the project a code of work breakdown is outside of, and several other lines.
    expect(
      say(
        {
          code: "WBS_ELEMENT_OUTSIDE_PROJECT",
          params: { wbs_element: "P9-SP", project_code: "P9" },
        },
        "fr",
      ),
    ).toContain(
      "Élément d’OTP lu\u00A0: «\u00A0P9-SP\u00A0». Code projet lu\u00A0: «\u00A0P9\u00A0».",
    );
    expect(say({ code: "DUPLICATE_COST_LINE", params: { rows: [4, 6, 7] } }, "fr")).toContain(
      "Autres lignes du fichier de même pièce et de même poste\u00A0: 4, 6 et 7.",
    );
  });

  it("says the day without a working hour in the language of the reader, from the refusal of a start or of a finish [WF-PLA-0020-A]", () => {
    const refused = fromExample("task_date_non_working_day", TASK_ON_SATURDAY);
    expect(say(refused, "fr")).toBe(
      "Les données saisies ne sont pas valides. Le samedi 19 décembre n’est pas travaillé sur le " +
        "calendrier de la tâche ; saisis le lundi 21 décembre.",
    );
    // The refusal of a finish (`/finish/date`) carries the same parameters, and reads the same.
    const finish = {
      code: "NON_WORKING_DAY",
      params: { date: "2027-01-16", next_working_day: "2027-01-18" },
    } as const;
    expect(say({ code: "VALIDATION_FAILED", fields: [finish] }, "fr")).toContain(
      "Le samedi 16 janvier n’est pas travaillé sur le calendrier de la tâche ; saisis le lundi 18 janvier.",
    );
  });

  it("says the default calendar, not the one of a task, when the planning start date of a structure is refused [WF-PLA-0020-A]", () => {
    const refused = fromExample("structure_start_non_working_day", {
      code: "VALIDATION_FAILED",
      fields: [
        {
          pointer: "/planning_start_on",
          code: "NON_WORKING_DAY",
          params: { date: "2026-12-19", next_working_day: "2026-12-21" },
        },
      ],
    });
    expect(say(refused, "fr")).toBe(
      "Les données saisies ne sont pas valides. Le samedi 19 décembre n’est pas travaillé sur le " +
        "calendrier par défaut ; saisis le lundi 21 décembre.",
    );
    expect(say(refused, "en")).toContain("is not worked on the default calendar; enter");
    // A task's date keeps the calendar of the task.
    expect(say(fromExample("task_date_non_working_day", TASK_ON_SATURDAY), "en")).toContain(
      "is not worked on the calendar of the task; enter",
    );
  });

  it("tells the dates a summary task takes from its subordinates, in the language of the reader, when a file corrects its manual mode [WF-PLA-0040-A]", () => {
    const signal = {
      code: "SUMMARY_TASK_DERIVED",
      params: { start: "2026-03-02", finish: "2026-04-30" },
    } as const;
    expect(say(signal, "en")).toBe(
      "A summary task takes its values from its subtasks. Its dates run from Monday 2 March to Thursday 30 April, those of its subtasks.",
    );
    expect(say({ code: "SUMMARY_TASK_DERIVED", params: { start: "2026-03-02" } }, "en")).toBe(
      "A summary task takes its values from its subtasks.",
    );
  });

  it("keeps the short sentence alone when the day without a working hour is not fully given [WF-PLA-0020-A]", () => {
    const short = "Date on a day without a working hour.";
    expect(say({ code: "NON_WORKING_DAY" }, "en")).toBe(short);
    expect(say({ code: "NON_WORKING_DAY", params: {} }, "en")).toBe(short);
    expect(
      say(
        { code: "NON_WORKING_DAY", params: { date: "2027-01-16", next_working_day: "soon" } },
        "en",
      ),
    ).toBe(short);
    expect(say({ code: "NON_WORKING_DAY", params: { date: "2027-01-16" } }, "en")).toBe(short);
    expect(
      say(
        { code: "NON_WORKING_DAY", params: { date: 20270116, next_working_day: "2027-01-18" } },
        "en",
      ),
    ).toBe(short);
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

  it("says each reason a refusal gives for the field it was reduced to, once [WF-PLA-0170-A]", () => {
    // `task_attach_exclusive_attached`, reduced to its first field's code as `byField` does: two
    // reasons on `/work_package_id`, a third on another field that is not this one's.
    const refused = fromExample("task_attach_exclusive_attached", {
      code: "VALIDATION_FAILED",
      fields: [
        { pointer: "/work_package_id", code: "WORK_BREAKDOWN_ITEMS_EXCLUSIVE" },
        {
          pointer: "/work_package_id",
          code: "WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED",
          params: {
            conflicting_object_id: "01926f3a-7c00-7000-8000-000000000551",
            conflicting_object_label: "Poste de commande",
          },
        },
        { pointer: "/order_item_id", code: "WORK_BREAKDOWN_ITEMS_EXCLUSIVE" },
      ],
    });
    const reduced = { ...refused, code: "WORK_BREAKDOWN_ITEMS_EXCLUSIVE" } as const;
    expect(say(reduced, "fr")).toBe(
      "Une tâche porte un lot ou un poste, jamais les deux. Ce lot ou ce poste est déjà porté par une autre tâche.",
    );
  });

  it("says why a code cannot name the tab of a sub-project: the characters it bears, or its reserved name [WF-PRJ-0050-A]", () => {
    // La création d'un sous-projet de code « SP/01 » ou « Synthèse » est refusée.
    const { fields } = fromExample("subproject_code_invalid", {
      code: "VALIDATION_FAILED",
      fields: [
        {
          pointer: "/code",
          code: "SUBPROJECT_CODE_INVALID",
          params: { forbidden_characters: ["/"] },
        },
      ],
    });
    expect(say({ code: "SUBPROJECT_CODE_INVALID", fields }, "fr")).toBe(
      "Ce code ne peut pas nommer l’onglet du sous-projet dans le fichier de reste à engager. Caractères interdits dans le code\u00A0: /.",
    );
    const reserved = fromExample("subproject_code_reserved", {
      code: "VALIDATION_FAILED",
      fields: [
        {
          pointer: "/code",
          code: "SUBPROJECT_CODE_INVALID",
          params: { reserved_name: "Synthèse" },
        },
      ],
    });
    expect(say(reserved, "fr")).toMatch(/ «\u00A0Synthèse\u00A0» est un nom réservé/);
    expect(say(reserved, "en")).toMatch(/ “Synthèse” is a reserved name/);
    // Neither a list of characters that is empty, nor a name that is no text, says anything.
    expect(
      say(
        { code: "SUBPROJECT_CODE_INVALID", params: { forbidden_characters: [], reserved_name: 3 } },
        "en",
      ),
    ).toBe("This code cannot name the tab of the subproject in the estimate-to-complete file.");
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
      "Les données saisies ne sont pas valides. Valeur maximale\u00A0: 1. Valeur minimale\u00A0: 0. Valeur maximale\u00A0: 0,75.",
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

  it("names the loop a link would close, its tasks in the order of the links, in the reader's language [WF-PLA-0030-A]", () => {
    const refused = fromExample("predecessors_cycle_refused", {
      code: "LINK_CYCLE",
      params: {
        cycle: [
          { node_id: "01926f3a-7c00-7000-8000-000000000556", label: "Réception usine" },
          {
            node_id: "01926f3a-7c00-7000-8000-000000000562",
            label: "Montage des armoires sur site",
          },
          { node_id: "01926f3a-7c00-7000-8000-000000000565", label: "Mise en service" },
        ],
      },
    });
    expect(say(refused, "fr")).toBe(
      "Cette liaison créerait une boucle. Boucle de liaisons, dans l’ordre : «\u00A0Réception usine\u00A0», " +
        "«\u00A0Montage des armoires sur site\u00A0» et «\u00A0Mise en service\u00A0».",
    );
    expect(say(refused, "en")).toBe(
      "This link would create a loop. Loop of links, in order: “Réception usine”, " +
        "“Montage des armoires sur site” and “Mise en service”.",
    );
    // A loop without its labels names nothing.
    expect(say({ code: "LINK_CYCLE", params: { cycle: [{ node_id: "n" }] } }, "en")).toBe(
      "This link would create a loop.",
    );
  });

  it("says a token without session identifier refuses an undo or a redo, in the reader's language [WF-IHM-0110-A]", () => {
    expect(say({ code: "SESSION_ID_MISSING" }, "fr")).toBe(
      "Votre jeton de session ne porte pas d’identifiant de session : reconnectez-vous pour pouvoir annuler ou rétablir une modification.",
    );
    expect(say({ code: "SESSION_ID_MISSING" }, "en")).toBe(
      "Your session token carries no session identifier: sign in again to be able to undo or redo a change.",
    );
  });

  it("says a move that would put a node under itself, in the reader's language [WF-PLA-0040-A]", () => {
    // `nodes_move_node_cycle`: the refusal of a parent taken among the moved nodes or their
    // subordinates, without a parameter. The example is read by what it must say, not by a shape
    // assumed for it: if the generated example changes, the assertion fails here.
    expect(example("nodes_move_node_cycle")).toMatchObject({ fields: [{ code: "NODE_CYCLE" }] });
    const reduced: ProblemText = { code: "NODE_CYCLE" };
    expect(say(reduced, "fr")).toBe("Ce déplacement mettrait un nœud sous lui-même.");
    expect(say(reduced, "en")).toBe("This move would put a node under itself.");
  });

  it.each<{ example: string; refusal: ProblemText; fr: string; en: string }>([
    {
      example: "structure_merge_report_link_forbidden",
      refusal: {
        code: "LINK_FORBIDDEN",
        params: {
          link: [
            { node_id: "01926f3a-7c00-7000-8000-000000000561", label: "Installation sur site" },
            {
              node_id: "01926f3a-7c00-7000-8000-000000000562",
              label: "Montage des armoires sur site",
            },
          ],
        },
      },
      fr: "Cette liaison n’est pas permise. Liaison en cause, la récapitulative d’abord\u00A0: «\u00A0Installation sur site\u00A0» et «\u00A0Montage des armoires sur site\u00A0».",
      en: "This link is not allowed. Link concerned, the summary first: “Installation sur site” and “Montage des armoires sur site”.",
    },
    {
      example: "structure_merge_report_horizon_exceeded",
      refusal: {
        code: "PROJECT_HORIZON_EXCEEDED",
        params: {
          task: { node_id: "01926f3a-7c00-7000-8000-000000000565", label: "Mise en service" },
        },
      },
      fr: "La durée du projet dépasserait quinze ans. Tâche en cause\u00A0: «\u00A0Mise en service\u00A0».",
      en: "The duration of the project would exceed fifteen years. Task concerned: “Mise en service”.",
    },
  ])(
    "names the tasks a refusal of the merge report gives, in the reader's language [WF-PLA-0030-A] [WF-PLA-0150-A] ($example)",
    ({ example: name, refusal, fr, en }) => {
      expect(example(name)).toMatchObject({ refusals: [refusal] });
      expect(say(refusal, "fr")).toBe(fr);
      expect(say(refusal, "en")).toBe(en);
    },
  );

  it("names the task a refused write gives, as the contract says it, in the reader's language [WF-PLA-0150-A]", () => {
    const refusal = fromExample("task_horizon_exceeded", {
      code: "PROJECT_HORIZON_EXCEEDED",
      params: {
        task: { node_id: "01926f3a-7c00-7000-8000-000000000523", label: "Pupitres opérateurs" },
      },
    });
    expect(say(refusal, "fr")).toBe(
      "La durée du projet dépasserait quinze ans. Tâche en cause\u00A0: «\u00A0Pupitres opérateurs\u00A0».",
    );
    expect(say(refusal, "en")).toBe(
      "The duration of the project would exceed fifteen years. Task concerned: “Pupitres opérateurs”.",
    );
  });

  it("says nothing of a link or a task without labels", () => {
    expect(say({ code: "LINK_FORBIDDEN", params: { link: [{ node_id: "n" }] } }, "en")).toBe(
      "This link is not allowed.",
    );
    expect(
      say({ code: "PROJECT_HORIZON_EXCEEDED", params: { task: { node_id: "n" } } }, "en"),
    ).toBe("The duration of the project would exceed fifteen years.");
  });

  it("names the format and the version a file was expected in [WF-INTF-0070-A]", () => {
    const problem = fromExample("import_format_unreadable", {
      code: "FILE_FORMAT_UNREADABLE",
      params: { expected_format: "estimate", expected_version: "1" },
    });
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
        max_columns: "12",
        component: "toString",
        work_package_task: { node_id: "01926f3a-7c00-7000-8000-000000000501" },
      },
    };
    expect(say(problem, "en")).toBe("The current state does not allow this operation.");
    // A lock version, the one parameter of a refusal of a stale version, names nothing either.
    const stale = fromExample("paste_stale", {
      code: "STALE_LOCK_VERSION",
      params: { expected_lock_version: 4 },
    });
    expect(say(stale, "en")).toBe(
      "Someone changed this data in the meantime; reload it to see its latest version.",
    );
    const unlabelled = { missing_prerequisites: ["constructor", "__proto__"] };
    expect(say({ code: "REFERENCE_INCOMPLETE", params: unlabelled }, "en")).toBe(
      "The minimum reference data is incomplete.",
    );
  });
});
