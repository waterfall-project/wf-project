// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sentence of a refusal, rendered from its code and parameters (WF-ARC-0110): the API
 * sends no text, the catalogue of the reader's language writes it.
 *
 * The code gives the sentence, `errors.<CODE>`; each parameter the contract names and a
 * reader can use adds one, `problemDetails.<param>`, with the value named by the catalogue
 * too — a `missing_permission` by its label, a `missing_condition` by its own, a `state` by its
 * label in the enumeration the envelope names with it (`state_enum`, #413), the object it is the
 * state of named by the sentence, the lines that bear a sub-project (`estimate_lines`) by their
 * numbers and their labels, the roles a nature or a category keeps in labour (`resource_roles`) by
 * their labels and codes, the projects a calendar would leave a task without hours in (`projects`)
 * by their labels and codes — a project without one by its label alone (WF-PLA-0010) —, the task of a
 * lot and those of its posts a write would move out of its subtree (`work_package_task`,
 * `order_item_tasks`, WF-PLA-0170) by their labels, the lines and the projects beyond a few
 * counted, the notice listing them, the characters a code of a sub-project cannot bear and the
 * reserved name it bears (`forbidden_characters`, `reserved_name`, WF-PRJ-0050), the sub-project a line of a started task does not leave
 * (`subproject`, WF-PRJ-0050) by its label, what a line imported is rejected for as the file bears it (`value`, `label`
 * and `tasks`, `wbs_element`, `project_code`, `rows`); a state without its enumeration,
 * or of an enumeration the catalogue does not know, adds nothing. A parameter that names nothing a
 * reader knows — an identifier, a lock version — adds nothing, but why a task would have no
 * working hour (`resource_role_ids`): the calendar of its one role, which has no hour, or those of
 * its roles, which never overlap, named when the screen read them (`ProblemLanguage.names`), or,
 * none given, the default calendar of a task without a line of labour — the refusal of a line
 * imported names these roles itself (`resource_roles`, #768). The parameters several refusals
 * share are typed by the contract (`ProblemParams`), read as they are; the others stay open, their
 * shape checked before they are said. The
 * parameters of a refusal by field (`fields[].params`, convention #293) are read alike, after those
 * of the envelope: the smallest or the largest value a field admits (`minimum`, `maximum`) is said
 * with the refusal, and a form says the refusal of each field at the field, by the same sentence
 * (`problemMessage` of the field's code and parameters); the day a date entered falls on without a
 * working hour, and the working day that follows (`date`, `next_working_day`), are written as days
 * of the week in the language of the reader — the server names them, the front computes nothing. The
 * decoder of the envelope (`src/api/problem.ts`) classes a refusal by its status, and the
 * notice of its outcome (`OutcomeNotice`) writes it with this sentence.
 */
import { createTranslator } from "next-intl";

import type { components } from "@/api/generated/schema";

import type { Catalogue } from "./catalogues";
import { formatDecimal, formatLocale, formatPlanningDay, isPlanningDate } from "./format";
import type { Locale } from "./locale";

/**
 * What the sentence is made of: the code of the envelope, its parameters, and those of its refusals
 * by field — a refusal by field is itself a code and its parameters.
 */
export type ProblemText = Pick<components["schemas"]["Problem"], "code" | "params"> & {
  readonly fields?: readonly Pick<components["schemas"]["FieldProblem"], "params">[] | undefined;
};

/** The language to write in, its catalogue, and the names of the objects the screen read. */
export interface ProblemLanguage {
  readonly locale: Locale;
  readonly messages: Catalogue;
  /**
   * The names of the objects the screen read, by identifier: what names the roles a refusal gives by
   * their identifiers alone (`resource_role_ids`); none, and they are left unnamed.
   */
  readonly names?: Readonly<Record<string, string>> | undefined;
}

/** Name a code a parameter carries — `users.write`, `revision_draft` — by its label. */
type Label = (list: string, value: unknown) => string | undefined;

/** The sentence of a parameter, `problemDetails.<param>`, and the values it is written with. */
type Detail = readonly [
  keyof Catalogue["problemDetails"],
  Readonly<Record<string, string | number>>,
];

/** Write a sentence of `problemDetails` with its values: a part a reader names a value by. */
export type Say = (key: Detail[0], values: Detail[1]) => string;

/**
 * The parameters of a refusal (`ProblemParams`): those several refusals share typed by the contract,
 * the others open, which a reader checks the shape of before it says them.
 */
type Params = components["schemas"]["ProblemParams"];

/** Read one parameter of the envelope: its sentence, or `undefined` when it has nothing to say. */
type Reader = (
  params: Readonly<Params>,
  label: Label,
  locale: Locale,
  say: Say,
  names: Readonly<Record<string, string>>,
) => Detail | undefined;

/** A line of an estimate a refusal names (`estimate_lines`): its number and its label. */
export type NamedLine = Pick<components["schemas"]["ProblemEstimateLine"], "row_number" | "label">;

/**
 * How many lines — or projects — a refusal names in its sentence; beyond, the sentence counts them,
 * and the notice of the refusal lists them under it (`namedLines`, `namedProjects`).
 */
export const LINES_IN_SENTENCE = 5;

/** The name of a line a refusal names, by its number — as the grid shows it — and its label. */
export function lineName({ row_number, label }: NamedLine, say: Say): string {
  return say("estimateLine", { row: String(row_number), label });
}

/**
 * The lines the parameters of a refusal name (`estimate_lines`), each by its number in its whole
 * structure and its label, in the order of the server.
 */
export function namedLines(params: Readonly<Params> | undefined): readonly NamedLine[] {
  return params?.estimate_lines ?? [];
}

/** A list of names joined as the language of the reader joins them: « a, b et c ». */
function conjunction(names: readonly string[], locale: Locale): string {
  return new Intl.ListFormat(formatLocale(locale), { type: "conjunction" }).format(names);
}

/** The items of a list a parameter holds that have the shape given; none for any other value. */
function itemsOf<T>(value: unknown, shaped: (item: unknown) => item is T): T[] {
  return (Array.isArray(value) ? value : []).filter(shaped);
}

/** A project a refusal names by its label and its code, null for one without (`projects`). */
export type NamedProject = components["schemas"]["ProblemProject"];

/**
 * Whether a value is an object a refusal names by its label: a task of a parameter the contract
 * leaves open (`work_package_task`, `order_item_tasks`, `cycle` ; EP-14/L42s).
 */
function isLabelled(value: unknown): value is { readonly label: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    "label" in value &&
    typeof value.label === "string"
  );
}

/** The projects the parameters of a refusal name (`projects`), in the order of the server. */
export function namedProjects(params: Readonly<Params> | undefined): readonly NamedProject[] {
  return params?.projects ?? [];
}

/** The name of a project a refusal names: its label and its code, its label alone without one. */
export function projectName({ project_label, project_code }: NamedProject, say: Say): string {
  return project_code === null
    ? project_label
    : say("codedName", { code: project_code, label: project_label });
}

/** An enumeration of the contract a refused state is a value of (`Problem.params.state_enum`). */
type StateEnumeration = components["schemas"]["StateEnumeration"];

/**
 * How a refused state is told, by its enumeration: the list of the catalogue that labels its
 * values, and the sentence that names the object it is the state of. An enumeration the contract
 * adds is a key the types ask for here.
 */
const STATES: Readonly<Record<StateEnumeration, { list: string; detail: Detail[0] }>> = {
  ProjectState: { list: "enums.ProjectState", detail: "projectState" },
};

/**
 * The conditions a nature or a category misses while roles keep it in labour (`resource_roles`,
 * WF-REF-0030, WF-REF-0040), and the object the roles are to be attached away from.
 */
const KEPT_IN_LABOUR: Readonly<Record<string, "cost_type" | "cost_category">> = {
  cost_type_without_role: "cost_type",
  cost_category_without_role: "cost_category",
};

/** The parameters of the envelope a reader is told about, in the order they are told. */
const DETAILS: readonly Reader[] = [
  ({ missing_permission }, label) => {
    const permission = label("permissions", missing_permission);
    return permission === undefined ? undefined : ["missing_permission", { permission }];
  },
  ({ missing_condition }, label) => {
    const condition = label("enums.CommandCondition", missing_condition);
    return condition === undefined ? undefined : ["missing_condition", { condition }];
  },
  ({ missing_prerequisites }, label, locale) => {
    const items = Array.isArray(missing_prerequisites) ? missing_prerequisites : [];
    const named = items.map((item) => label("enums.ReferenceReadiness.missing", item));
    const known = named.filter((item) => item !== undefined);
    const list = conjunction(known, locale);
    return known.length === 0 ? undefined : ["missing_prerequisites", { prerequisites: list }];
  },
  // The lines that bear a sub-project its deletion is refused for, each by its number in its whole
  // structure — as the grid shows it, never grouped — and its label (EP-14/L42q); beyond a few,
  // counted, the notice listing them.
  (params, _label, locale, say) => {
    const lines = namedLines(params);
    if (lines.length > LINES_IN_SENTENCE) {
      return ["estimate_lines_listed", { count: lines.length }];
    }
    const named = lines.map((line) => lineName(line, say));
    return named.length === 0
      ? undefined
      : ["estimate_lines", { lines: conjunction(named, locale) }];
  },
  // The roles that keep a nature or a category in labour, to attach first to another category of
  // labour — outside the nature, for a nature — (WF-REF-0030, WF-REF-0040, WF-IHM-0090).
  ({ resource_roles = [], missing_condition }, _label, locale, say) => {
    const of =
      typeof missing_condition === "string" && Object.hasOwn(KEPT_IN_LABOUR, missing_condition)
        ? KEPT_IN_LABOUR[missing_condition]
        : undefined;
    const named = resource_roles.map(({ code, label }) => say("codedName", { code, label }));
    return of === undefined || named.length === 0
      ? undefined
      : ["resource_roles", { roles: conjunction(named, locale), of }];
  },
  // Why a task would have no working hour (WF-PLA-0010): the roles whose calendars never overlap —
  // named by the refusal of a line imported (`resource_roles`, #768), or given by their identifiers
  // alone and named as the screen read them (`resource_role_ids`); none given, the default calendar
  // of a task without a line of labour.
  ({ resource_roles, resource_role_ids, missing_condition }, _label, locale, say, names) => {
    if (resource_roles !== undefined && missing_condition === undefined) {
      const roles = resource_roles.map(({ code, label }) => say("codedName", { code, label }));
      return roles.length === 0
        ? ["resource_role_ids_none", {}]
        : ["resource_role_ids", { roles: conjunction(roles, locale), count: roles.length }];
    }
    if (Array.isArray(resource_role_ids) && resource_role_ids.length === 0) {
      return ["resource_role_ids_none", {}];
    }
    const ids = itemsOf(resource_role_ids, (id): id is string => typeof id === "string");
    const named = ids.map((id) => names[id]).filter((name) => name !== undefined);
    if (ids.length === 0) {
      return undefined;
    }
    // One role alone: its calendar has no hour; several: their calendars never overlap.
    const count = ids.length;
    return named.length === 0
      ? ["resource_role_ids_unnamed", { count }]
      : ["resource_role_ids", { roles: conjunction(named, locale), count }];
  },
  // Each project by its label and its code, by its label alone without one (WF-PLA-0010); beyond a
  // few, counted, the notice listing them.
  (params, _label, locale, say) => {
    const projects = namedProjects(params);
    if (projects.length > LINES_IN_SENTENCE) {
      return ["projects_listed", { count: projects.length }];
    }
    const named = projects.map((project) => projectName(project, say));
    return named.length === 0 ? undefined : ["projects", { projects: conjunction(named, locale) }];
  },
  // The task of a lot and those of its posts a write would move out of its subtree, by their labels
  // (WF-PLA-0170, WF-IHM-0080).
  ({ work_package_task }, _label, _locale, say) =>
    isLabelled(work_package_task)
      ? ["work_package_task", { task: say("taskName", { label: work_package_task.label }) }]
      : undefined,
  ({ order_item_tasks }, _label, locale, say) => {
    const named = itemsOf(order_item_tasks, isLabelled).map(({ label }) =>
      say("taskName", { label }),
    );
    return named.length === 0
      ? undefined
      : ["order_item_tasks", { tasks: conjunction(named, locale), count: named.length }];
  },
  // The tasks of the loop that links entered would close, each by its label, in the order of the
  // links (`LINK_CYCLE`, WF-PLA-0030): the reason is named to the one who entered them.
  ({ cycle }, _label, locale, say) => {
    const named = itemsOf(cycle, isLabelled).map(({ label }) => say("taskName", { label }));
    return named.length === 0 ? undefined : ["cycle", { tasks: conjunction(named, locale) }];
  },
  // The two tasks of a link a summary cannot bear to one of its subordinates, the summary first,
  // each by its label (`LINK_FORBIDDEN`, WF-PLA-0030, #1582).
  ({ link }, _label, locale, say) => {
    const named = itemsOf(link, isLabelled).map(({ label }) => say("taskName", { label }));
    return named.length === 0 ? undefined : ["link", { tasks: conjunction(named, locale) }];
  },
  // The task a write or a merge that would carry the project past the fifteen years it may last is
  // refused for, by its label (`PROJECT_HORIZON_EXCEEDED`, WF-PLA-0150, #788): the contract says
  // only « the task concerned », which is not always the one that ends the project.
  ({ task }, _label, _locale, say) =>
    isLabelled(task)
      ? ["horizon_task", { task: say("taskName", { label: task.label }) }]
      : undefined,
  // The day a date entered falls on without an hour worked, and the working day that follows, both
  // given by the server and written in the language of the reader (`NON_WORKING_DAY`, WF-PLA-0020).
  ({ date, next_working_day }, _label, locale) =>
    typeof date === "string" &&
    typeof next_working_day === "string" &&
    isPlanningDate(date) &&
    isPlanningDate(next_working_day)
      ? [
          "non_working_day",
          {
            date: formatPlanningDay(date, locale),
            next: formatPlanningDay(next_working_day, locale),
          },
        ]
      : undefined,
  // The dates a summary task takes from its subordinates, given by the server and written in the
  // language of the reader (`SUMMARY_TASK_DERIVED`, WF-PLA-0040): what an import corrects of the
  // summary task a file holds in manual mode.
  ({ start, finish }, _label, locale) =>
    typeof start === "string" &&
    typeof finish === "string" &&
    isPlanningDate(start) &&
    isPlanningDate(finish)
      ? [
          "summary_dates",
          { start: formatPlanningDay(start, locale), finish: formatPlanningDay(finish, locale) },
        ]
      : undefined,
  // The sub-project a line of a started task does not leave, because it received actual costs, by
  // its label (`SUBPROJECT_HAS_ACTUAL_COSTS`, WF-PRJ-0050, #1066).
  ({ subproject }) =>
    subproject === undefined ? undefined : ["subproject", { label: subproject.label }],
  // What a line of a file imported is rejected for, named as the file bears it: the value it holds
  // that no object has (`UNKNOWN_TASK`, `UNKNOWN_RESOURCE_ROLE`, `UNKNOWN_SUBPROJECT`, `value`), the
  // label that several tasks share, with those tasks (`AMBIGUOUS_TASK_LABEL`, `label`, `tasks`,
  // WF-INTF-0120), the element of work breakdown, and the project code it bears
  // (`WBS_ELEMENT_INVALID`, `WBS_ELEMENT_OUTSIDE_PROJECT`, WF-CRE-0020), and the ranks of the other
  // lines of the same document and item (`DUPLICATE_COST_LINE`, `rows`, WF-INTF-0080).
  ({ value }) => (typeof value === "string" ? ["unknown_value", { value }] : undefined),
  ({ label, tasks }, _label, locale, say) => {
    const named = itemsOf(tasks, isLabelled).map((task) => say("taskName", { label: task.label }));
    return typeof label === "string" && named.length > 0
      ? ["ambiguous_label", { label, tasks: conjunction(named, locale) }]
      : undefined;
  },
  ({ wbs_element }) =>
    typeof wbs_element === "string" ? ["wbs_element", { element: wbs_element }] : undefined,
  ({ project_code }) =>
    typeof project_code === "string" ? ["project_code", { code: project_code }] : undefined,
  ({ rows }, _label, locale) => {
    const ranks = itemsOf(rows, (row): row is number => typeof row === "number");
    return ranks.length === 0
      ? undefined
      : ["duplicate_rows", { count: ranks.length, rows: conjunction(ranks.map(String), locale) }];
  },
  ({ state, state_enum }, label) => {
    const told =
      typeof state_enum === "string" && Object.hasOwn(STATES, state_enum)
        ? STATES[state_enum]
        : undefined;
    const named = told === undefined ? undefined : label(told.list, state);
    return told === undefined || named === undefined ? undefined : [told.detail, { state: named }];
  },
  // Why a code cannot name the tab of a sub-project: the characters it bears that a tab cannot, or
  // the name it bears that is reserved, as the server gives them (`SUBPROJECT_CODE_INVALID`,
  // WF-PRJ-0050).
  ({ forbidden_characters }) => {
    const characters = itemsOf(
      forbidden_characters,
      (item): item is string => typeof item === "string",
    );
    return characters.length === 0
      ? undefined
      : ["forbidden_characters", { characters: characters.join(" ") }];
  },
  ({ reserved_name }) =>
    typeof reserved_name === "string" ? ["reserved_name", { name: reserved_name }] : undefined,
  ({ max_columns }) =>
    typeof max_columns === "number" ? ["max_columns", { max_columns }] : undefined,
  ({ minimum }, _label, locale) => bound("minimum", minimum, locale),
  ({ maximum }, _label, locale) => bound("maximum", maximum, locale),
  ({ component }, label) => {
    const name = label("enums.PlatformComponent", component);
    return name === undefined ? undefined : ["component", { component: name }];
  },
  ({ expected_format }, label) => {
    const format = label("enums.ExchangeKind", expected_format);
    return format === undefined ? undefined : ["expected_format", { format }];
  },
  ({ expected_version }) =>
    typeof expected_version === "string"
      ? ["expected_version", { version: expected_version }]
      : undefined,
  // The columns of an extraction of actual costs the correspondence leaves without a label
  // (`STATE_FORBIDS_OPERATION`, `actual_cost_mapping_complete`, WF-REF-0190), each by its name.
  ({ columns = [], missing_condition }, label) => {
    if (missing_condition !== "actual_cost_mapping_complete") {
      return undefined;
    }
    const named = columns.flatMap((column) => label("enums.ActualCostSourceColumn", column) ?? []);
    return named.length === 0
      ? undefined
      : ["columns", { count: named.length, columns: named.join(", ") }];
  },
  // The columns required that a file of actual costs lacks, each with the labels the correspondence
  // declares for it (`FILE_FORMAT_UNREADABLE`, WF-REF-0190, WF-INTF-0070).
  ({ missing_columns = [] }, label, locale, say) => {
    const named = missing_columns.flatMap(({ column, labels }) => {
      const name = label("enums.ActualCostSourceColumn", column);
      if (name === undefined) {
        return [];
      }
      const declared = labels.map((each) => say("declaredLabel", { label: each }));
      return declared.length === 0
        ? [name]
        : [
            say("missingColumn", {
              column: name,
              count: declared.length,
              labels: conjunction(declared, locale),
            }),
          ];
    });
    return named.length === 0
      ? undefined
      : ["missing_columns", { count: named.length, columns: conjunction(named, locale) }];
  },
];

/** A decimal of the contract — `Decimal`, `Money` —, which a bound may be written in. */
const DECIMAL = /^-?\d+(\.\d+)?$/;

/**
 * The sentence of a bound a value crosses (`minimum`, `maximum`): a number, or a decimal or an amount
 * of the contract written in the language of the reader; nothing for any other value — a date, which
 * the filter of a period says by itself.
 */
function bound(key: "minimum" | "maximum", value: unknown, locale: Locale): Detail | undefined {
  if (typeof value === "number") {
    return [key, { [key]: value }];
  }
  return typeof value === "string" && DECIMAL.test(value)
    ? [key, { [key]: formatDecimal(value, locale) }]
    : undefined;
}

/** Whether a value is a node of the catalogue that holds others. */
function isList(node: unknown): node is Readonly<Record<string, unknown>> {
  return typeof node === "object" && node !== null;
}

/**
 * The label a list of the catalogue gives a code: `users.write` under `permissions` is
 * `permissions.users.write`. The code comes from the envelope, which the types cannot know,
 * so the catalogue is walked rather than typed; a label is plain text, with no argument.
 */
function labelIn(messages: Catalogue): Label {
  return (list, value) => {
    if (typeof value !== "string") {
      return undefined;
    }
    let node: unknown = messages;
    for (const part of [...list.split("."), ...value.split(".")]) {
      node = isList(node) && Object.hasOwn(node, part) ? node[part] : undefined;
    }
    return typeof node === "string" ? node : undefined;
  };
}

/** Render a refusal of the API as a sentence in the reader's language. */
export function problemMessage(
  problem: ProblemText,
  { locale, messages, names = {} }: ProblemLanguage,
): string {
  const t = createTranslator({ locale, messages });
  const label = labelIn(messages);
  const say: Say = (key, values) => t(`problemDetails.${key}`, values);
  const every = [
    problem.params ?? {},
    ...(problem.fields ?? []).map((field) => field.params ?? {}),
  ];
  const details = every
    .flatMap((params) => DETAILS.map((detail) => detail(params, label, locale, say, names)))
    .filter((detail) => detail !== undefined)
    .map(([key, values]) => say(key, values));
  return [t(`errors.${problem.code}`), ...details].join(" ");
}
