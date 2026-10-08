// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import type { GridConfig } from "./columns";
import { ESTIMATE_FIELDS, ESTIMATE_GRID as ESTIMATE_GRID_READ, estimateGrid } from "./estimate";
import {
  COMMON_FIELDS,
  type NodeField,
  type NodeFields,
  type NodeList,
  type NodeRow,
  type NodeSortColumn,
  type NodeTotals,
  nodeFieldNames,
  projectNodes,
  SPARSE_LINE_FIELDS,
} from "./nodes";
import { PLANNING_FIELDS, PLANNING_GRID } from "./planning";
import { REMAINING_FIELDS, remainingGrid } from "./remaining";

/** The facet of a node that is a task. */
type TaskFacet = components["schemas"]["TaskFacet"];

/** The facet of a node that is a line of the estimate. */
type EstimateLineFacet = components["schemas"]["EstimateLineFacet"];

/**
 * How long a reading of the six thousand rows of the volume may take, twice rendered: seconds
 * under the other tests, and more under the coverage.
 */
const VOLUME_TIMEOUT = 60_000;

/**
 * The answers of `listNodes` among the examples of the contract: the witness, those of each grid,
 * the milestone, and the structure of the volumes of §4.6.2, which the fake back serves.
 */
const ANSWERS = [
  "nodes",
  "nodes_estimate",
  "nodes_planning",
  "nodes_milestone",
  "volume/nodes_thousand",
];

/**
 * The keys a projection keeps of an object: those of a closed list that the object has — a field
 * the answer leaves out stays out.
 */
function keptKeys(source: object, fields: readonly string[]): string[] {
  return fields.filter((key) => key in source).sort();
}

/**
 * The keys a projection keeps of a line: those of a closed list that the line has, but a field
 * that says nothing — null, or a false flag (`SPARSE_LINE_FIELDS`).
 */
function keptLineKeys(source: object, fields: readonly string[]): string[] {
  const sparse = new Set<string>(SPARSE_LINE_FIELDS);
  return keptKeys(source, fields).filter((key) => {
    const value: unknown = (source as Record<string, unknown>)[key];
    return !sparse.has(key) || (value !== null && value !== false);
  });
}

/** An answer of `listNodes`, among the examples of the contract. */
function answer(name: string): NodeList {
  return example(name) as NodeList;
}

/**
 * Everything a grid reads of its rows, row by row: the key, the number, the level, how the label
 * stands out, the value of each column — that it formats, sorts and totals —, which of its cells
 * the server computes and the field each asks the server about, which are entered and the value
 * each entry starts from, and the markup of the icon of the nature and of each cell its column
 * renders.
 */
function whatTheGridReads<Row>(
  config: GridConfig<Row, NodeSortColumn, NodeTotals>,
  rows: readonly Row[],
) {
  const values = rows.map((row) => [
    config.rowKey(row),
    config.rowNumber?.(row),
    config.tree?.level(row),
    config.tree?.emphasis?.(row),
    ...config.columns.map((column) => column.value(row)),
    ...config.columns.map((column) =>
      column.computed?.in(row) === true ? column.computed.field(row) : null,
    ),
    ...config.columns.map((column) =>
      column.entry?.in(row) === true ? column.entry.value(row) : null,
    ),
  ]);
  const markup = renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {rows.map((row) => (
        <p key={config.rowKey(row)}>
          {config.tree?.nature(row)}
          {config.columns.map((column) => (
            <span key={column.key}>{column.render?.(row)}</span>
          ))}
        </p>
      ))}
    </NextIntlClientProvider>,
  );
  return { values, markup };
}

/**
 * The rows a page hands a grid keep all it reads of the answer — the page shows the same grid —,
 * and nothing else: they weigh no more than a share of the answer, measured on the volume.
 */
function holdsWhatTheGridReads<
  N extends NodeField,
  T extends keyof TaskFacet,
  L extends keyof EstimateLineFacet,
>(
  grid: string,
  config: GridConfig<NodeRow<N, T, L>, NodeSortColumn, NodeTotals>,
  fields: NodeFields<N, T, L>,
  share: number,
) {
  const node = [...COMMON_FIELDS.node, ...fields.node, "task", "estimate_line"];
  const task = [...COMMON_FIELDS.task, ...fields.task];
  const line = [...COMMON_FIELDS.line, ...fields.line];

  describe(`the rows the page hands the grid of the ${grid}`, () => {
    it.each(ANSWERS)(
      "keep all the grid reads of the answer %s, the totals as they are",
      (name) => {
        const list = answer(name);
        const projected = projectNodes(list, fields);
        expect(projected.totals).toBe(list.totals);
        expect(projected.items).toHaveLength(list.items.length);
        const read = whatTheGridReads(config, projected.items);
        expect(read).toEqual(whatTheGridReads(config, list.items));
        expect(read.markup).toContain('role="img"');
      },
      VOLUME_TIMEOUT,
    );

    it.each(ANSWERS)(
      "keep of each node of the answer %s its listed fields, and those alone",
      (name) => {
        const list = answer(name);
        const rows = projectNodes(list, fields).items;
        for (const [index, source] of list.items.entries()) {
          const row = rows[index] ?? {};
          expect(Object.keys(row).sort()).toEqual(keptKeys(source, node));
          expect(Object.keys(("task" in row ? row.task : undefined) ?? {}).sort()).toEqual(
            keptKeys(source.task ?? {}, task),
          );
          expect(
            Object.keys(("estimate_line" in row ? row.estimate_line : undefined) ?? {}).sort(),
          ).toEqual(keptLineKeys(source.estimate_line ?? {}, line));
          for (const [key, value] of Object.entries(row)) {
            if (key !== "task" && key !== "estimate_line") {
              expect(value).toEqual(source[key as NodeField]);
            }
          }
        }
      },
    );

    it("are those the page asks listNodes for, each field of a facet named by its facet", () => {
      const names = nodeFieldNames(fields);
      expect(new Set(names).size).toBe(names.length);
      // As the contract writes a name: a field of the node, or of a facet after its name.
      expect(names.filter((name) => !/^((task|estimate_line)\.)?[a-z_]+$/.test(name))).toEqual([]);
      expect([...names].sort()).toEqual(
        [
          ...node.filter((key) => key !== "task" && key !== "estimate_line"),
          ...task.map((key) => `task.${key}`),
          ...line.map((key) => `estimate_line.${key}`),
        ].sort(),
      );
    });

    it(`weigh less than ${share.toString()} of the answer on the volume`, () => {
      const list = answer("volume/nodes_thousand");
      const projected = projectNodes(list, fields);
      expect(JSON.stringify(projected).length).toBeLessThan(JSON.stringify(list).length * share);
    });
  });
}

describe("a field of a line that says nothing, left out by the projection", () => {
  it("is read by the grid of the estimate as the null it was: the same values, the same cells", () => {
    const list = answer("nodes_estimate");
    const projected = projectNodes(list, ESTIMATE_FIELDS).items;
    // The provision: out of any sub-project, no deactivated object; its payment delay, nought,
    // says something and is kept (WF-DEV-0020).
    const provision = projected.find((node) => node.estimate_line?.is_computed === true);
    expect(provision?.estimate_line).not.toHaveProperty("subproject_label");
    expect(provision?.estimate_line?.payment_delay_days).toBe(0);
    expect(provision?.estimate_line).not.toHaveProperty("uses_inactive_object");
    const config = ESTIMATE_GRID_READ;
    for (const key of ["subproject", "inactive_object"]) {
      const column = config.columns.find((each) => each.key === key);
      const source = list.items.find((node) => node.node_id === provision?.node_id);
      if (column === undefined || provision === undefined || source === undefined) {
        throw new Error(`no column ${key}, or no provision, in the estimate`);
      }
      expect(column.value(provision) ?? null).toBeNull();
      expect(column.value(provision)).toEqual(column.value(source));
    }
    expect(whatTheGridReads(config, projected)).toEqual(whatTheGridReads(config, list.items));
  });
});

// The shares the projections weigh on the volume, as measured, each bound a hundredth or less above
// it: 0.640 for the estimate, 0.455 for the planning — what each node accepts (`editable_fields`,
// #219) counted, whose weight #238 weighs. The labels of a line and the amounts at the year of
// reference and corrected for inflation (#235, #305) made the answer heavier, 6.46 million
// characters for 5.70: the estimate reads two labels and two amounts where it read one amount, and
// its rows grew from 3.43 to 3.83 million; the planning reads none of them, its rows stayed at 2.94
// million, a smaller share of a larger answer. The sub-project, its identifier and its label, the
// payment delay and the deactivated object of a line (WF-DEV-0050, WF-REF-0010, #349) took the
// rows of the estimate from 3.83 to 4.37 million, 0.593 to 0.675 of the same answer; left out
// where they say nothing (`SPARSE_LINE_FIELDS`), 4.13 million, 0.640 — 3.96 million, 0.613, in a
// grid that enters no sub-project, which its identifier does not reach (`withoutSubprojectIds`).
// The parent of each node, by which the tree folds (EP-02/L40), took the rows of the estimate from
// 4.18 to 4.48 million characters of the 6.91 of the volume, 0.604 to 0.649; those of the planning
// from 2.98 to 3.29 million, 0.431 to 0.476; those of the remaining to commit from 3.80 to 4.11
// million, 0.550 to 0.594.
/** Nothing is written by these tests: what an entry reads is all they look at. */
function unwritten(): never {
  throw new Error("nothing is written here");
}

// The grid of the estimate of a revision open to entry: its categories and roles named, its cells
// entered, which read the label, the category, the role and the figures of a line.
const ENTERED_ESTIMATE = estimateGrid(estimateReference(), {
  line: unwritten,
  task: unwritten,
  paste: { preview: unwritten, apply: unwritten, span: unwritten, name: unwritten },
});

holdsWhatTheGridReads("estimate", ENTERED_ESTIMATE, ESTIMATE_FIELDS, 0.655);
holdsWhatTheGridReads("planning", PLANNING_GRID, PLANNING_FIELDS, 0.485);
// The grid of the remaining to commit of a revision open to entry, which reads the figures of a
// line, whether it takes a re-estimation, its three amounts, and the progress and finish of a task:
// 3.80 million characters of the 6.51 of the volume, 0.584 (US-0230/L1); the figures at the previous
// remaining to commit (#424), left out where they say nothing, as they do before the first review.
holdsWhatTheGridReads(
  "remaining to commit",
  remainingGrid({ line: unwritten }),
  REMAINING_FIELDS,
  0.6,
);
