// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sentence of a refusal, rendered from its code and parameters (WF-ARC-0110): the API
 * sends no text, the catalogue of the reader's language writes it.
 *
 * The code gives the sentence, `errors.<CODE>`; each parameter the contract names and a
 * reader can use adds one, `problemDetails.<param>`, with the value named by the catalogue
 * too — a `missing_permission` by its label, a `missing_condition` by its own. A parameter
 * that names nothing a reader knows — an identifier, a lock version — adds nothing. The
 * decoder of the envelope (`src/api/problem.ts`) classes a refusal by its status, and the
 * notice of its outcome (`OutcomeNotice`) writes it with this sentence.
 */
import { createTranslator } from "next-intl";

import type { components } from "@/api/generated/schema";

import type { Catalogue } from "./catalogues";
import { formatLocale } from "./format";
import type { Locale } from "./locale";

/** What the sentence is made of: the code of the envelope, and its parameters. */
export type ProblemText = Pick<components["schemas"]["Problem"], "code" | "params">;

/** The language to write in, and its catalogue. */
export interface ProblemLanguage {
  readonly locale: Locale;
  readonly messages: Catalogue;
}

/** Name a code a parameter carries — `users.write`, `revision_draft` — by its label. */
type Label = (list: string, value: unknown) => string | undefined;

/** The sentence of a parameter, `problemDetails.<param>`, and the values it is written with. */
type Detail = readonly [
  keyof Catalogue["problemDetails"],
  Readonly<Record<string, string | number>>,
];

/** Read one parameter of the envelope: its sentence, or `undefined` when it has nothing to say. */
type Reader = (
  params: Readonly<Record<string, unknown>>,
  label: Label,
  locale: Locale,
) => Detail | undefined;

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
    const list = new Intl.ListFormat(formatLocale(locale), { type: "conjunction" }).format(known);
    return known.length === 0 ? undefined : ["missing_prerequisites", { prerequisites: list }];
  },
  ({ max_columns }) =>
    typeof max_columns === "number" ? ["max_columns", { max_columns }] : undefined,
  ({ component }, label) => {
    const name = label("enums.PlatformComponent", component);
    return name === undefined ? undefined : ["component", { component: name }];
  },
];

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
  { locale, messages }: ProblemLanguage,
): string {
  const t = createTranslator({ locale, messages });
  const label = labelIn(messages);
  const params = problem.params ?? {};
  const details = DETAILS.map((detail) => detail(params, label, locale))
    .filter((detail) => detail !== undefined)
    .map(([key, values]) => t(`problemDetails.${key}`, values));
  return [t(`errors.${problem.code}`), ...details].join(" ");
}
