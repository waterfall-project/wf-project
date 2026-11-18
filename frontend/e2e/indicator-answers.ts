// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the service answers to the reads of the indicators screen, for the paths that hold what the
 * screen shows to it (US-1730, WF-ARC-0070-A): the same operation, for the same revision, the same
 * date and the same scope, read by the API under the token of the account of the run, and the figures
 * written as the front writes them — by `src/i18n/format.ts`, from the strings of the answer, never by a
 * sum, a ratio nor a rounding of the path. A figure of the screen that differs from its answer is the
 * front's own.
 */
import { type APIRequestContext, type Browser, expect, type Locator } from "@playwright/test";

import catalogue from "../messages/fr.json" with { type: "json" };
import type { components } from "../src/api/generated/schema";
import { formatDecimal, formatMoney, formatPlanningDate, formatShare } from "../src/i18n/format";
import { API, frontToken, type Person } from "./service/realm";

type Schemas = components["schemas"];

export type Indicators = Schemas["ProjectIndicators"];
export type IndexHistory = Schemas["IndexHistory"];
export type CurveSeries = Schemas["CurveSeries"];
export type MilestoneTracking = Schemas["MilestoneTracking"];
type Computable = Schemas["Computable"];

/** The language of the catalogue the paths read, and of the figures they write. */
export const LOCALE = "fr";

/** The way a path reads the API: its headers, its currency. */
export interface Reader {
  readonly get: (path: string, query?: Record<string, string>) => Promise<Answer>;
  readonly currency: string | undefined;
}

/** An answer of the API: its status, its body. */
export interface Answer {
  readonly status: number;
  readonly body: unknown;
}

/** The API read as the account of the run does, in the currency of the installation. */
export async function readerOf(
  browser: Browser,
  request: APIRequestContext,
  person: Person | undefined,
): Promise<Reader> {
  if (person === undefined) {
    throw new Error("the account of the run exists against the service only");
  }
  const headers = { Authorization: `Bearer ${await frontToken(browser, person)}` };
  const get = async (path: string, query: Record<string, string> = {}): Promise<Answer> => {
    const search = new URLSearchParams(query).toString();
    const answer = await request.get(`${API}${path}${search === "" ? "" : `?${search}`}`, {
      headers,
    });
    return { status: answer.status(), body: await answer.json() };
  };
  const settings = await get("/reference/settings");
  const code = (settings.body as Schemas["ReferenceSettings"]).currency_code;
  return { get, currency: code };
}

/** The answer of an operation, which must be a 200. */
export async function ok<T>(reader: Reader, path: string, query?: Record<string, string>) {
  const answer = await reader.get(path, query);
  expect(answer.status, `GET ${path}`).toBe(200);
  return answer.body as T;
}

/** How a share is worded when its rounding would show it as nil: the catalogue's words. */
const WORDS = (side: "below" | "above", values: { readonly share: string }): string =>
  catalogue.share[side].replace("{share}", values.share);

/** What a card shows of a value: its text, and the reason it gives when not computable. */
interface Shown {
  readonly text: string;
  readonly reason?: string;
}

/** The sentence of the reason a value is not computable, in the catalogue. */
function reasonOf(value: Computable): string | undefined {
  return value.reason === null ? undefined : catalogue.enums.NotComputableReason[value.reason];
}

/** What a card shows for a value under `Computable`: written, or « Non calculable » and its reason. */
function shown(value: Computable, write: (digits: string) => string): Shown {
  if (value.is_computable && value.value !== null) {
    return { text: write(value.value) };
  }
  const reason = reasonOf(value);
  return { text: catalogue.indicator.notComputable, ...(reason === undefined ? {} : { reason }) };
}

/** What a cell of a table shows for a value under `Computable`. */
function inCell(value: Computable, write: (digits: string) => string): string {
  if (value.is_computable && value.value !== null) {
    return write(value.value);
  }
  const reason = reasonOf(value);
  return reason === undefined
    ? catalogue.indicator.notComputable
    : catalogue.projectIndicators.notComputable.replace("{reason}", reason);
}

/** An amount as the screen writes it. */
export function money(amount: string, reader: Reader): string {
  return formatMoney(amount, LOCALE, reader.currency);
}

/** A share, an index, an amount: how each indicator of a card is written. */
const writeShare = (digits: string) => formatShare(digits, LOCALE, WORDS);
const writeIndex = (digits: string) => formatDecimal(digits, LOCALE);
const share = (value: Computable) => shown(value, writeShare);

/**
 * The definition that follows a term of a card, named as the card names it: the name of a term is
 * not computed from its content, so the term is found by its text.
 */
function definitionOf(card: Locator, term: string): Locator {
  return card
    .locator("dt")
    .filter({ hasText: new RegExp(`^${term.replaceAll(/[()]/g, String.raw`\$&`)}$`) })
    .first()
    .locator("xpath=following-sibling::*[1]");
}

/** Expect each figure of a card — a term and the text of its definition — as the API answers. */
async function expectFigures(
  card: Locator,
  figures: readonly (readonly [string, string | Shown])[],
) {
  for (const [term, expected] of figures) {
    const text = typeof expected === "string" ? expected : expected.text;
    await expect(definitionOf(card, term), term).toHaveText(text);
    if (typeof expected !== "string" && expected.reason !== undefined) {
      await expect(definitionOf(card, term).locator("xpath=.."), term).toContainText(
        expected.reason,
      );
    }
  }
}

/**
 * Expect every figure of the five cards of the indicators to be the answer of the API: the amounts,
 * the shares, the indices and their zones, the three projections and their variances.
 */
export async function expectCards(main: Locator, indicators: Indicators, reader: Reader) {
  const names = catalogue.projectIndicators;
  const figures = names.figures;
  const amount = (value: string) => money(value, reader);
  const card = (title: string) => main.getByRole("region", { name: title, exact: true });
  const indices = catalogue.indicator.names;
  const { projections } = indicators;
  await expectFigures(card(names.financial.title), [
    [indices.financialProgress, share(indicators.financial_progress)],
    [indices.budgetConsumption, share(indicators.budget_consumption)],
    [figures.actualCost, amount(indicators.actual_cost)],
    [figures.remaining, amount(indicators.remaining)],
    [figures.referenceBudget, amount(indicators.reference_budget)],
  ]);
  const projection = card(names.projections.title);
  const row = (label: string) => projection.getByRole("row", { name: new RegExp(`^${label}`) });
  const optional = (value: string | null | undefined) =>
    value === null || value === undefined ? "" : amount(value);
  for (const [label, cells] of [
    [names.projections.atBudget, [projections.at_budget, projections.variance_at_budget]],
    [
      names.projections.projectManager,
      [projections.project_manager, projections.variance_project_manager],
    ],
  ] as const) {
    const [total, variance] = cells;
    await expect(row(label).getByRole("cell")).toHaveText([optional(total), optional(variance)]);
  }
  await expectFigures(projection, [
    [indices.projectionAtObservedRate, shown(projections.at_observed_rate, amount)],
  ]);
  if (projections.variance_at_observed_rate !== null) {
    await expect(projection).toContainText(
      names.projections.varianceAtObservedRate.replace(
        "{variance}",
        amount(projections.variance_at_observed_rate),
      ),
    );
  }
  await expectFigures(card(names.physical.title), [
    [indices.physicalProgress, share(indicators.physical_progress)],
    [figures.earnedValue, amount(indicators.earned_value)],
    [figures.referenceBudget, amount(indicators.reference_budget)],
  ]);
  const zones = catalogue.enums.AlertZone;
  for (const [title, kind, value, rest] of [
    [
      names.cost.title,
      indices.costIndex,
      indicators.cost_index,
      [
        [figures.costVariance, amount(indicators.cost_variance)],
        [figures.earnedValue, amount(indicators.earned_value)],
        [figures.actualCost, amount(indicators.actual_cost)],
      ],
    ],
    [
      names.schedule.title,
      indices.scheduleIndex,
      indicators.schedule_index,
      [
        [figures.scheduleVariance, amount(indicators.schedule_variance)],
        [figures.earnedValue, amount(indicators.earned_value)],
        [figures.plannedValue, amount(indicators.planned_value)],
      ],
    ],
  ] as const) {
    await expectFigures(card(title), [[kind, shown(value.value, writeIndex)], ...rest]);
    // The zone is the API's: the signal beside the index, written by its name when the API gives
    // one, and absent when it gives none.
    const signal = definitionOf(card(title), kind).locator("xpath=../following-sibling::span");
    if (value.zone === null) {
      await expect(signal, `the zone of ${kind}`).toHaveCount(0);
    } else {
      await expect(signal, `the zone of ${kind}`).toHaveText(zones[value.zone]);
    }
  }
}

/** The text of each cell of each row of a table, under its header, as the screen holds it. */
async function cellsOf(table: Locator): Promise<string[][]> {
  await expect(table, "the table of the values is on the screen").toHaveCount(1);
  return table
    .locator("tbody tr")
    .evaluateAll((rows) =>
      rows.map((row) => [...row.querySelectorAll("th, td")].map((cell) => cell.textContent.trim())),
    );
}

/**
 * The table of the values of a figure, folded under « Valeurs du graphique » — hidden, so found by
 * its tag rather than by its role.
 */
function valuesOf(figure: Locator, caption?: string): Locator {
  const tables = figure.locator("table");
  return caption === undefined
    ? tables.first()
    : tables.filter({ has: figure.page().locator("caption", { hasText: caption }) });
}

/** Expect the table of the values of a curve figure to hold the points of the answer, in order. */
export async function expectCurvePoints(
  figure: Locator,
  curves: CurveSeries,
  reader: Reader,
  { cashOut = false }: { readonly cashOut?: boolean } = {},
) {
  const wanted = curves.series.flatMap((series) =>
    series.points.map((point) => [
      formatPlanningDate(point.date, LOCALE),
      money(point.amount, reader),
    ]),
  );
  expect(wanted.length, "the answer holds points to compare").toBeGreaterThan(0);
  const cells = await cellsOf(valuesOf(figure));
  expect(
    cells.map(([, date, amount]) => [date, amount]),
    "the points of the curves",
  ).toEqual(wanted);
  const months = curves.cash_out_by_month ?? [];
  if (cashOut) {
    expect(months.length, "the answer holds a cash-out to compare").toBeGreaterThan(0);
  }
  if (months.length === 0 && !cashOut) {
    // No cash-out to read, none asked: the screen offers no table of them either.
    await expect(
      valuesOf(figure, catalogue.projectIndicators.curves.cashOut),
      "no table of the cash-out when the answer holds none",
    ).toHaveCount(0);
  }
  if (months.length > 0) {
    const shifted = await cellsOf(valuesOf(figure, catalogue.projectIndicators.curves.cashOut));
    expect(
      shifted.map(([, past, forecast]) => [past, forecast]),
      "the cash-out by month",
    ).toEqual(months.map((month) => [money(month.past, reader), money(month.forecast, reader)]));
  }
}

/** Expect the table of the values of the evolution of an index to hold the points of the answer. */
export async function expectIndexPoints(
  figure: Locator,
  history: IndexHistory,
  kind: "cost_index" | "schedule_index",
) {
  const zones = catalogue.enums.AlertZone;
  const wanted = history.scopes.flatMap((scope) =>
    scope.points.map((point) => [
      point.version_name ?? catalogue.projectIndicators.history.currentRevision,
      inCell(point[kind].value, writeIndex),
      point[kind].zone === null ? "" : zones[point[kind].zone],
    ]),
  );
  expect(wanted.length, "the answer holds points to compare").toBeGreaterThan(0);
  const cells = await cellsOf(valuesOf(figure));
  expect(
    cells.map(([, revision, , value, zone]) => [revision, value, zone]),
    "the points of the evolution",
  ).toEqual(wanted);
}

/** Expect the table of the time/time diagram to hold the forecasts of the answer, in order. */
export async function expectMilestonePoints(figure: Locator, tracking: MilestoneTracking) {
  const wanted = tracking.milestones.flatMap((milestone) =>
    milestone.points.map((point) => [
      milestone.label,
      formatPlanningDate(point.forecast_date, LOCALE),
      milestone.completed_on === null
        ? catalogue.projectIndicators.milestones.notCompleted
        : formatPlanningDate(milestone.completed_on, LOCALE),
    ]),
  );
  expect(wanted.length, "the answer holds points to compare").toBeGreaterThan(0);
  const cells = await cellsOf(valuesOf(figure));
  expect(
    cells.map(([label = "", , forecast = "", completed = ""]) => [label, forecast, completed]),
    "the points of the tracking",
  ).toEqual(wanted);
}
