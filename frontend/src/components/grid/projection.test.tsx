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
import { ESTIMATE_FIELDS, estimateGrid } from "./estimate";
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
} from "./nodes";
import { PLANNING_FIELDS, PLANNING_GRID } from "./planning";

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
          ).toEqual(keptKeys(source.estimate_line ?? {}, line));
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

// The shares the projections weigh on the volume, as measured: 0.602 for the estimate, 0.516 for
// the planning — what each node accepts (`editable_fields`, #219) counted, whose weight #238
// weighs.
/** Nothing is written by these tests: what an entry reads is all they look at. */
function unwritten(): never {
  throw new Error("nothing is written here");
}

// The grid of the estimate of a revision open to entry: its categories and roles named, its cells
// entered, which read the label, the category, the role and the figures of a line.
const ENTERED_ESTIMATE = estimateGrid(estimateReference(), "?", {
  line: unwritten,
  task: unwritten,
  paste: { preview: unwritten, apply: unwritten, span: unwritten, name: unwritten },
});

holdsWhatTheGridReads("estimate", ENTERED_ESTIMATE, ESTIMATE_FIELDS, 0.61);
holdsWhatTheGridReads("planning", PLANNING_GRID, PLANNING_FIELDS, 0.52);
