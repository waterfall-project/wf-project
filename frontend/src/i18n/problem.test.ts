// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import type { NodeList } from "@/components/grid/nodes";
import { example } from "@/test/fixtures";

import { CATALOGUES } from "./catalogues";
import type { Locale } from "./locale";
import {
  LINES_IN_SENTENCE,
  namedLines,
  namedProjects,
  problemMessage,
  type ProblemText,
} from "./problem";

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

/** The first projects of the portfolio of the witness, as a refusal names them (`projects`). */
function portfolioProjects(count: number) {
  const portfolio = example("volume/portfolio_projects") as {
    items: { label: string; code: string | null }[];
  };
  return portfolio.items
    .slice(0, count)
    .map(({ label, code }) => ({ project_label: label, project_code: code }));
}

/** The monteur câbleur and the electrical engineer of the witness, as a refusal gives them. */
const FITTER = "01926f3a-7c00-7000-8000-000000000454";
const ENGINEER = "01926f3a-7c00-7000-8000-000000000451";

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

  it.each([
    [
      "session_revoked",
      "fr",
      "Votre session a été fermée — déconnexion, désactivation du compte ou retrait de ses rôles ; reconnectez-vous en saisissant à nouveau vos identifiants.",
    ],
    [
      "session_revoked",
      "en",
      "Your session has been closed — by a sign-out, the deactivation of the account or the withdrawal of its roles; sign in again with your credentials.",
    ],
    ["session_expired", "fr", "Votre session a expiré ; reconnectez-vous."],
    ["session_expired", "en", "Your session has expired; please sign in again."],
  ] as const)(
    "says a session closed — whose sign-in asks for the identifiers again — apart from one expired (#855): %s, %s",
    (name, locale, sentence) => {
      expect(say(example(name) as ProblemText, locale)).toBe(sentence);
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
      params: { missing_condition: "revision_draft" },
    };
    expect(say(problem, "fr")).toBe(
      "L\u2019état actuel ne permet pas cette opération. Condition non remplie\u00A0: révision en cours d\u2019élaboration.",
    );
    expect(say(problem, "en")).toBe(
      "The current state does not allow this operation. Unmet condition: draft revision.",
    );
  });

  it("names the columns of the correspondence without a label, and the columns a file lacks with the labels declared for them [WF-REF-0190-A]", () => {
    const refused = example("import_actual_cost_mapping_incomplete") as ProblemText;
    expect(say(refused, "en")).toBe(
      "The current state does not allow this operation. Unmet condition: actual-cost extraction mapping complete. Required columns without a label: WBS element, Document no., Document date, Amount.",
    );
    const missing = example("import_actual_costs_column_missing") as ProblemText;
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
    const refused = example("import_actual_cost_mapping_incomplete") as ProblemText;
    const other = {
      ...refused,
      params: { ...refused.params, missing_condition: "may_create_revision" },
    } as ProblemText;
    expect(say(other, "en")).not.toContain("without a label");
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

  it("names no line of an empty list, the condition alone said", () => {
    // The lines are typed by the contract (`ProblemParams.estimate_lines`, #768): a malformed one is
    // a type error, no longer a case the sentence reads.
    const { params, ...refused } = example("subproject_delete_estimated") as ProblemText;
    const condition =
      "The current state does not allow this operation. Unmet condition: no estimate line of the " +
      "current revision bearing the subproject.";
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
        structure_label: "Structure principale",
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

  it("names the sub-project a line of a started task does not leave, which received actual costs, from the refusal of its field (#1066)", () => {
    const refused = example("estimate_line_subproject_has_actual_costs") as ProblemText;
    expect(say(refused, "fr")).toBe(
      "Les données saisies ne sont pas valides. Sous-projet qui a reçu des coûts réels, que la " +
        "ligne ne quitte pas : « Poste de commande ».",
    );
    expect(say(refused, "en")).toBe(
      "The data entered is not valid. Subproject that has received actual costs, which the line " +
        "does not leave: “Poste de commande”.",
    );
    // The refusal of the field, said at the field, by its own code and the same sub-project.
    expect(refused.fields?.[0]?.params).toBeDefined();
    const params = refused.fields?.[0]?.params ?? {};
    expect(say({ code: "SUBPROJECT_HAS_ACTUAL_COSTS", params }, "fr")).toBe(
      "Cette ligne ne peut pas quitter ce sous-projet : sa tâche est démarrée, et le " +
        "sous-projet a reçu des coûts réels. Sous-projet qui a reçu des coûts réels, que la ligne " +
        "ne quitte pas : « Poste de commande ».",
    );
  });

  it("says the day without a working hour in the language of the reader, from the refusal of a start or of a finish [WF-PLA-0020-A]", () => {
    const refused = example("task_date_non_working_day") as ProblemText;
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

  it("names the roles a category keeps in labour by their labels and codes, to attach first to another category of labour [WF-REF-0040-A]", () => {
    // Le rattachement […] d'une catégorie […] à laquelle un rôle de ressource est rattaché, à une
    // nature hors main-d'œuvre est refusé : the roles named, which the screen of the costs may not
    // read (EP-14/L42r).
    const refused = example("cost_category_role_kind_refused") as ProblemText;
    expect(say(refused, "fr")).toBe(
      "L’état actuel ne permet pas cette opération. Condition non remplie\u00A0: catégorie " +
        "rattachée à aucun rôle de ressource. Rôles à rattacher d’abord à une autre catégorie de " +
        "main-d’œuvre\u00A0: Automaticien (AUTOM).",
    );
    expect(say(refused, "en")).toBe(
      "The current state does not allow this operation. Unmet condition: category attached to no " +
        "resource role. Roles to attach first to another labour category: Automaticien (AUTOM).",
    );
  });

  it("names the roles a nature keeps in labour, to attach first to a category of another nature", () => {
    // The refusal of a nature has no example of its own: it takes the form of that of a category
    // (EP-14/L42r), whose condition this variant of `cost_category_role_kind_refused` alone changes.
    const { params, ...refused } = example("cost_category_role_kind_refused") as ProblemText;
    const nature = {
      ...refused,
      params: { ...params, missing_condition: "cost_type_without_role" as const },
    };
    expect(say(nature, "fr")).toMatch(
      /Rôles à rattacher d’abord à une catégorie de main-d’œuvre d’une autre nature\u00A0: Automaticien \(AUTOM\)\.$/,
    );
  });

  it("names each project a calendar would leave a task without hours in by its label and its code, one without by its label alone [WF-PLA-0010-A]", () => {
    // La modification d'un calendrier qui laisserait une tâche sans heure dans un projet que le
    // manager ne peut pas consulter est refusée en nommant ce projet par son libellé et son code ;
    // un projet en chiffrage sans code est nommé par son seul libellé.
    const refused = example("calendar_update_without_hours") as ProblemText;
    const hours =
      "Une tâche n’aurait plus aucune heure travaillée dans la semaine. Le calendrier de son rôle " +
      "n’a aucune heure.";
    expect(say(refused, "fr")).toBe(
      `${hours} Projets en cause\u00A0: Modernisation du poste de commande (PRJ-001).`,
    );
    // A variant of `calendar_update_without_hours`: the project without a code, the one value
    // changed — an offer in pricing, which no code names yet.
    const uncoded = {
      ...refused.params,
      projects: namedProjects(refused.params).map((project) => ({
        ...project,
        project_code: null,
      })),
    };
    expect(say({ ...refused, params: uncoded }, "fr")).toBe(
      `${hours} Projets en cause\u00A0: Modernisation du poste de commande.`,
    );
  });

  it("names the role whose calendar has no hour as the screen read it, and says the cause unnamed when it read none", () => {
    // The one role of `calendar_update_without_hours`, the fitter: its calendar has no hour.
    const refused = example("calendar_update_without_hours") as ProblemText;
    const named = problemMessage(refused, {
      locale: "en",
      messages: CATALOGUES.en,
      names: { [FITTER]: "Monteur câbleur (MONT-CAB)" },
    });
    expect(named).toBe(
      "A task would have no working hour left in the week. Role whose calendar has no hour: " +
        "Monteur câbleur (MONT-CAB). Projects involved: Modernisation du poste de commande " +
        "(PRJ-001).",
    );
    expect(say(refused, "en")).toBe(
      "A task would have no working hour left in the week. The calendar of its role has no hour. " +
        "Projects involved: Modernisation du poste de commande (PRJ-001).",
    );
  });

  it("names the roles whose calendars never overlap, two of them, as the screen read them, and says the cause unnamed when it read none", () => {
    // A variant of `calendar_update_without_hours`: two roles in cause, the fitter and the
    // electrical engineer, the one value changed.
    const refused = example("calendar_update_without_hours") as ProblemText;
    const two = {
      ...refused,
      params: { ...refused.params, resource_role_ids: [FITTER, ENGINEER] },
    };
    const named = problemMessage(two, {
      locale: "fr",
      messages: CATALOGUES.fr,
      names: {
        [FITTER]: "Monteur câbleur (MONT-CAB)",
        [ENGINEER]: "Ingénieur électricien (ING-ELEC)",
      },
    });
    expect(named).toBe(
      "Une tâche n’aurait plus aucune heure travaillée dans la semaine. Rôles dont les calendriers " +
        "ne se recoupent aucun jour\u00A0: Monteur câbleur (MONT-CAB) et Ingénieur électricien " +
        "(ING-ELEC). Projets en cause\u00A0: Modernisation du poste de commande (PRJ-001).",
    );
    expect(say(two, "fr")).toContain(" Les calendriers de ses rôles ne se recoupent aucun jour. ");
  });

  it("says a task without a line of labour on the default calendar when the refusal names no role, and no calendar of a role", () => {
    // A variant of `calendar_update_without_hours`: no role in cause, the one value changed — the
    // default calendar emptied, or another designated by default, which the tasks without a line
    // of labour follow (WF-REF-0120).
    const refused = example("calendar_update_without_hours") as ProblemText;
    const told = say({ ...refused, params: { ...refused.params, resource_role_ids: [] } }, "fr");
    expect(told).toBe(
      "Une tâche n’aurait plus aucune heure travaillée dans la semaine. Tâches sans ligne de " +
        "main-d’œuvre, sur le calendrier par défaut. Projets en cause\u00A0: Modernisation du " +
        "poste de commande (PRJ-001).",
    );
    expect(told).not.toMatch(/rôle/);
  });

  it("names the roles of a line imported that would leave its task without hours by their labels and codes, from the rejection of the contract [WF-PLA-0010-A]", () => {
    // The motive of a line imported names its roles itself (`resource_roles`); the example of the
    // contract carries the task too (`tasks`), which the sentence does not read (#768).
    const { report } = example("import_estimate_task_without_hours") as {
      report: { rejected: ProblemText[] };
    };
    const [line] = report.rejected;
    expect(line?.code).toBe("TASK_WITHOUT_WORKING_HOURS");
    expect(say(line as ProblemText, "fr")).toBe(
      "Une tâche n’aurait plus aucune heure travaillée dans la semaine. Rôles dont les " +
        "calendriers ne se recoupent aucun jour\u00A0: Monteur câbleur (MONT-CAB) et Technicien " +
        "de mise en service (TECH-MES).",
    );
  });

  it("does not tell the hours of a task for roles that a refusal of another code names, whose condition it gives [WF-PLA-0010-A]", () => {
    const refused = example("cost_category_role_kind_refused") as ProblemText;
    expect(say(refused, "fr")).not.toMatch(/heure travaillée/);
  });

  it("names five projects in its sentence, and counts none", () => {
    // A variant of `calendar_update_without_hours`: five projects of the portfolio in cause, the
    // one value changed — the most the sentence names.
    const refused = example("calendar_update_without_hours") as ProblemText;
    const projects = portfolioProjects(LINES_IN_SENTENCE);
    const told = say({ ...refused, params: { ...refused.params, projects } }, "fr");
    expect(told).toContain(
      "Projets en cause\u00A0: Modernisation du poste de commande (PRJ-001), Extension de la ligne " +
        "d'essais (PRJ-002),",
    );
    expect(told).toMatch(/ et Automatisation du poste de commande — Lyon \(PRJ-005\)\.$/);
    expect(told).not.toContain("listés ci-dessous");
  });

  it("counts the projects of a refusal beyond a few, which the notice lists", () => {
    // A variant of `calendar_update_without_hours`: six projects of the portfolio in cause, the one
    // value changed.
    const refused = example("calendar_update_without_hours") as ProblemText;
    const listed = { ...refused, params: { ...refused.params, projects: portfolioProjects(6) } };
    expect(say(listed, "fr")).toMatch(/ 6 projets en cause, listés ci-dessous\.$/);
    expect(namedProjects(listed.params)).toHaveLength(6);
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

  it("says why a code cannot name the tab of a sub-project: the characters it bears, or its reserved name [WF-PRJ-0050-A]", () => {
    // La création d'un sous-projet de code « SP/01 » ou « Synthèse » est refusée.
    const forbidden = example("subproject_code_invalid") as {
      fields: NonNullable<ProblemText["fields"]>;
    };
    expect(say({ code: "SUBPROJECT_CODE_INVALID", fields: forbidden.fields }, "fr")).toBe(
      "Ce code ne peut pas nommer l’onglet du sous-projet dans le fichier de reste à engager. Caractères interdits dans le code\u00A0: /.",
    );
    const reserved = example("subproject_code_reserved") as ProblemText;
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

  it("names the loop a link would close, its tasks in the order of the links, in the reader's language [WF-PLA-0030-A]", () => {
    const refused = example("predecessors_cycle_refused") as ProblemText;
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
        max_columns: "12",
        component: "toString",
        resource_role_ids: [453],
        work_package_task: { node_id: "01926f3a-7c00-7000-8000-000000000501" },
      },
    };
    expect(say(problem, "en")).toBe("The current state does not allow this operation.");
    // A lock version, the one parameter of a refusal of a stale version, names nothing either.
    const stale = example("paste_stale") as ProblemText;
    expect(say(stale, "en")).toBe(
      "Someone changed this data in the meantime; reload it to see its latest version.",
    );
    const unlabelled = { missing_prerequisites: ["constructor", "__proto__"] };
    expect(say({ code: "REFERENCE_INCOMPLETE", params: unlabelled }, "en")).toBe(
      "The minimum reference data is incomplete.",
    );
  });
});
