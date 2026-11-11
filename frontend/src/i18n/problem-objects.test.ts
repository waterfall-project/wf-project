// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";
import { fromExample, say } from "@/test/refusals";

import { LINES_IN_SENTENCE, namedLines, namedProjects, type ProblemText } from "./problem";

/** The refusal of the deletion of a sub-project lines bear (`subproject_delete_estimated`). */
const SUBPROJECT_ESTIMATED: ProblemText = {
  code: "STATE_FORBIDS_OPERATION",
  params: {
    missing_condition: "subproject_without_estimate_lines",
    estimate_lines: [
      {
        structure_id: "01926f3a-7c00-7000-8000-000000000201",
        structure_label: "Structure principale",
        node_id: "01926f3a-7c00-7000-8000-000000000553",
        row_number: 10,
        label: "Raccordement des borniers",
      },
      {
        structure_id: "01926f3a-7c00-7000-8000-000000000201",
        structure_label: "Structure principale",
        node_id: "01926f3a-7c00-7000-8000-000000000554",
        row_number: 11,
        label: "Borniers",
      },
    ],
  },
};

/** The refusal of a category a role keeps in labour (`cost_category_role_kind_refused`). */
const CATEGORY_WITH_ROLE: ProblemText = {
  code: "STATE_FORBIDS_OPERATION",
  params: {
    missing_condition: "cost_category_without_role",
    resource_roles: [
      {
        resource_role_id: "01926f3a-7c00-7000-8000-000000000453",
        code: "AUTOM",
        label: "Automaticien",
      },
    ],
  },
};

/**
 * The refusal of a calendar that would leave a task without hours
 * (`calendar_update_without_hours`).
 */
const CALENDAR_WITHOUT_HOURS: ProblemText = {
  code: "TASK_WITHOUT_WORKING_HOURS",
  params: {
    resource_roles: [
      {
        resource_role_id: "01926f3a-7c00-7000-8000-000000000454",
        code: "MONT-CAB",
        label: "Monteur câbleur",
      },
    ],
    projects: [{ project_label: "Modernisation du poste de commande", project_code: "PRJ-001" }],
  },
};

/**
 * The first projects of the portfolio of the witness (`volume/portfolio_projects`), in its order,
 * by what a refusal names of them.
 */
const PORTFOLIO = [
  { label: "Modernisation du poste de commande", code: "PRJ-001" },
  { label: "Extension de la ligne d'essais", code: "PRJ-002" },
  { label: "Extension du poste de commande — Lyon", code: "PRJ-003" },
  { label: "Rénovation du poste de commande — Lyon", code: "PRJ-004" },
  { label: "Automatisation du poste de commande — Lyon", code: "PRJ-005" },
  { label: "Mise en conformité du poste de commande — Lyon", code: "PRJ-006" },
] as const;

/** The first projects of the portfolio of the witness, as a refusal names them (`projects`). */
function portfolioProjects(count: number) {
  const projects = PORTFOLIO.slice(0, count);
  const portfolio = example("volume/portfolio_projects");
  projects.forEach((project, rank) => {
    expect(portfolio).toHaveProperty(["items", rank], expect.objectContaining(project));
  });
  return projects.map(({ label, code }) => ({ project_label: label, project_code: code }));
}

describe("the objects a refusal names", () => {
  it("names the lines that bear a sub-project its deletion is refused for, by their numbers and their labels, in the reader's language [WF-DAT-0080-A]", () => {
    // La suppression d'un sous-projet que portent des lignes de devis de la révision en cours est
    // refusée et nomme ces lignes.
    const refused = fromExample("subproject_delete_estimated", SUBPROJECT_ESTIMATED);
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
    const { params, ...refused } = fromExample("subproject_delete_estimated", SUBPROJECT_ESTIMATED);
    const condition =
      "The current state does not allow this operation. Unmet condition: no estimate line of the " +
      "current revision bearing the subproject.";
    expect(say({ ...refused, params: { ...params, estimate_lines: [] } }, "en")).toBe(condition);
  });

  it("counts the lines that bear a sub-project beyond a few, which the notice lists", () => {
    // A counterfactual variant of `subproject_delete_estimated`: the first six lines of the main
    // structure of the witness borne by the sub-project, the rest of the refusal kept.
    const refused = fromExample("subproject_delete_estimated", SUBPROJECT_ESTIMATED);
    // The first lines of `volume/nodes_thousand`, by their rank among its nodes.
    const volume = example("volume/nodes_thousand");
    const read = [
      [2, "000000000527", 3, "Ingénierie de détail"],
      [9, "000000000553", 10, "Raccordement des borniers"],
      [10, "000000000554", 11, "Borniers"],
      [11, "000000000555", 12, "Provision — risque de reprise du câblage"],
      [15, "000000000543", 16, "Frais de relance"],
      [17, "000000000545", 18, "Affrètement"],
    ] as const;
    expect(read).toHaveLength(LINES_IN_SENTENCE + 1);
    const lines = read.map(([rank, node, row_number, label]) => {
      const node_id = `01926f3a-7c00-7000-8000-${node}`;
      expect(volume).toHaveProperty(["items", rank, "node_id"], node_id);
      expect(volume).toHaveProperty(["items", rank, "row_number"], row_number);
      expect(volume).toHaveProperty(["items", rank, "estimate_line", "label"], label);
      return {
        structure_id: "01926f3a-7c00-7000-8000-000000000201",
        structure_label: "Structure principale",
        node_id,
        row_number,
        label,
      };
    });
    const listed = { ...refused, params: { ...refused.params, estimate_lines: lines } };
    expect(say(listed, "fr")).toMatch(
      /portant le sous-projet\. 6 lignes de devis de la révision en cours portent le sous-projet, listées ci-dessous\. Une ligne de provision change de sous-projet par son risque\.$/,
    );
    expect(namedLines(listed.params).map((line) => line.row_number)).toEqual(
      lines.map((line) => line.row_number),
    );
  });

  it("names the roles a category keeps in labour by their labels and codes, to attach first to another category of labour [WF-REF-0040-A]", () => {
    // Le rattachement […] d'une catégorie […] à laquelle un rôle de ressource est rattaché, à une
    // nature hors main-d'œuvre est refusé : the roles named, which the screen of the costs may not
    // read (EP-14/L42r).
    const refused = fromExample("cost_category_role_kind_refused", CATEGORY_WITH_ROLE);
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
    const { params, ...refused } = fromExample(
      "cost_category_role_kind_refused",
      CATEGORY_WITH_ROLE,
    );
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
    const refused = fromExample("calendar_update_without_hours", CALENDAR_WITHOUT_HOURS);
    const hours =
      "Une tâche n’aurait plus aucune heure travaillée dans la semaine. Rôle dont le calendrier " +
      "n’a aucune heure\u00A0: Monteur câbleur (MONT-CAB).";
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

  it("names the role whose calendar has no hour from the refusal itself, by its label and its code [WF-PLA-0010-A]", () => {
    // The one role of `calendar_update_without_hours`, the fitter: its calendar has no hour.
    const refused = fromExample("calendar_update_without_hours", CALENDAR_WITHOUT_HOURS);
    expect(say(refused, "en")).toBe(
      "A task would have no working hour left in the week. Role whose calendar has no hour: " +
        "Monteur câbleur (MONT-CAB). Projects involved: Modernisation du poste de commande " +
        "(PRJ-001).",
    );
  });

  it("names the roles whose calendars never overlap, two of them, from the refusal itself [WF-PLA-0010-A]", () => {
    // The roles of `nodes_move_without_hours`, the refusal of a move from the planning: the
    // engineer and the commissioning technician.
    const refused = fromExample("nodes_move_without_hours", {
      code: "TASK_WITHOUT_WORKING_HOURS",
      params: {
        resource_roles: [
          {
            resource_role_id: "01926f3a-7c00-7000-8000-000000000451",
            code: "ING-ELEC",
            label: "Ingénieur électricien",
          },
          {
            resource_role_id: "01926f3a-7c00-7000-8000-000000000452",
            code: "TECH-MES",
            label: "Technicien de mise en service",
          },
        ],
        tasks: [
          {
            project_id: "01926f3a-7c00-7000-8000-000000000001",
            node_id: "01926f3a-7c00-7000-8000-000000000552",
            label: "Câblage des armoires",
          },
        ],
      },
    });
    expect(say(refused, "fr")).toContain(
      "Rôles dont les calendriers ne se recoupent aucun jour\u00A0: Ingénieur électricien " +
        "(ING-ELEC) et Technicien de mise en service (TECH-MES).",
    );
  });

  it("says a task without a line of labour on the default calendar when the refusal names no role, and no calendar of a role [WF-PLA-0010-A]", () => {
    // `calendar_default_without_hours`: the default calendar emptied, or another designated by
    // default, which the tasks without a line of labour follow (WF-REF-0120).
    const refused = fromExample("calendar_default_without_hours", {
      code: "TASK_WITHOUT_WORKING_HOURS",
      params: {
        resource_roles: [],
        projects: [
          { project_label: "Modernisation du poste de commande", project_code: "PRJ-001" },
        ],
      },
    });
    expect(refused.params?.resource_roles).toEqual([]);
    const told = say(refused, "fr");
    expect(told).toContain("Tâches sans ligne de main-d’œuvre, sur le calendrier par défaut.");
    expect(told).not.toMatch(/rôle/);
  });

  it("names the roles of a line imported that would leave its task without hours by their labels and codes, from the rejection of the contract [WF-PLA-0010-A]", () => {
    // The motive of a line imported names its roles itself (`resource_roles`), and its task by its
    // label (`tasks`, #768).
    const line: ProblemText = {
      code: "TASK_WITHOUT_WORKING_HOURS",
      params: {
        resource_roles: [
          {
            resource_role_id: "01926f3a-7c00-7000-8000-000000000454",
            code: "MONT-CAB",
            label: "Monteur câbleur",
          },
          {
            resource_role_id: "01926f3a-7c00-7000-8000-000000000452",
            code: "TECH-MES",
            label: "Technicien de mise en service",
          },
        ],
        tasks: [
          { lineage_id: "01926f3a-7c00-7000-8000-000000000652", label: "Câblage des armoires" },
        ],
      },
    };
    expect(example("import_estimate_task_without_hours")).toMatchObject({
      report: { rejected: [line] },
    });
    expect(say(line, "fr")).toBe(
      "Une tâche n’aurait plus aucune heure travaillée dans la semaine. Rôles dont les " +
        "calendriers ne se recoupent aucun jour\u00A0: Monteur câbleur (MONT-CAB) et Technicien " +
        "de mise en service (TECH-MES). Tâche en cause\u00A0: «\u00A0Câblage des armoires\u00A0».",
    );
  });

  it("names the task a write would leave without hours by its label, and the role by its label and its code, from the refusal of the contract [WF-PLA-0010-A]", () => {
    const refused = fromExample("estimate_line_without_hours", {
      code: "TASK_WITHOUT_WORKING_HOURS",
      params: {
        resource_roles: [
          {
            resource_role_id: "01926f3a-7c00-7000-8000-000000000454",
            code: "MONT-CAB",
            label: "Monteur câbleur",
          },
        ],
        tasks: [
          {
            project_id: "01926f3a-7c00-7000-8000-000000000001",
            node_id: "01926f3a-7c00-7000-8000-000000000552",
            label: "Câblage des armoires",
          },
        ],
      },
    });
    expect(say(refused, "fr")).toBe(
      "Une tâche n’aurait plus aucune heure travaillée dans la semaine. Rôle dont le calendrier " +
        "n’a aucune heure\u00A0: Monteur câbleur (MONT-CAB). Tâche en cause\u00A0: " +
        "«\u00A0Câblage des armoires\u00A0».",
    );
  });

  it("names the categories that forbid a change of the type of a nature by their labels and codes, from the refusal of the contract [WF-REF-0030-A]", () => {
    const refused = fromExample("cost_type_kind_refused", {
      code: "STATE_FORBIDS_OPERATION",
      params: {
        missing_condition: "cost_type_unused",
        cost_categories: [
          {
            cost_category_id: "01926f3a-7c00-7000-8000-000000000401",
            code: "ACH-001",
            label: "Sous-traitance",
          },
          {
            cost_category_id: "01926f3a-7c00-7000-8000-000000000403",
            code: "ACH-002",
            label: "Matériel électrique",
          },
        ],
      },
    });
    const told = say(refused, "fr");
    expect(told).toContain(
      "Catégories de la nature à rattacher d’abord à une autre nature du même type\u00A0: " +
        "Sous-traitance (ACH-001) et Matériel électrique (ACH-002).",
    );
    expect(say(refused, "en")).toContain(
      "Sous-traitance (ACH-001) and Matériel électrique (ACH-002)",
    );
  });

  it("does not tell the hours of a task for roles that a refusal of another code names, whose condition it gives [WF-PLA-0010-A]", () => {
    const refused = fromExample("cost_category_role_kind_refused", CATEGORY_WITH_ROLE);
    expect(say(refused, "fr")).not.toMatch(/heure travaillée/);
  });

  it("names five projects in its sentence, and counts none", () => {
    // A variant of `calendar_update_without_hours`: five projects of the portfolio in cause, the
    // one value changed — the most the sentence names.
    const refused = fromExample("calendar_update_without_hours", CALENDAR_WITHOUT_HOURS);
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
    const refused = fromExample("calendar_update_without_hours", CALENDAR_WITHOUT_HOURS);
    const listed = { ...refused, params: { ...refused.params, projects: portfolioProjects(6) } };
    expect(say(listed, "fr")).toMatch(/ 6 projets en cause, listés ci-dessous\.$/);
    expect(namedProjects(listed.params)).toHaveLength(6);
  });
});
