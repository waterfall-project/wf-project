// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import type { GridConfig } from "./columns";
import { ESTIMATE_FIELDS, ESTIMATE_GRID } from "./estimate";
import {
  COMMON_FIELDS,
  type NodeField,
  type NodeFields,
  type NodeList,
  type NodeRow,
  type NodeSortColumn,
  type NodeTotals,
  projectNodes,
} from "./nodes";
import { PLANNING_FIELDS, PLANNING_GRID } from "./planning";
import { RowNumbers } from "./planning-cells";

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
 * the server computes and what their values depend on, and the markup of the icon of the nature
 * and of each cell its column renders, the predecessors named by the row numbers of the answer.
 */
function whatTheGridReads<Row>(
  config: GridConfig<Row, NodeSortColumn, NodeTotals>,
  rows: readonly Row[],
  numbers: ReadonlyMap<string, number>,
) {
  const values = rows.map((row, index) => [
    config.rowKey(row),
    config.rowNumber?.(row),
    config.tree?.level(row),
    config.tree?.emphasis?.(row),
    ...config.columns.map((column) => column.value(row)),
    ...config.columns.map((column) =>
      column.computed?.in(row) === true ? column.computed.dependsOn(rows, index) : null,
    ),
  ]);
  const markup = renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <RowNumbers value={numbers}>
        {rows.map((row) => (
          <p key={config.rowKey(row)}>
            {config.tree?.nature(row)}
            {config.columns.map((column) => (
              <span key={column.key}>{column.render?.(row)}</span>
            ))}
          </p>
        ))}
      </RowNumbers>
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
        const numbers = new Map(list.items.map((item) => [item.node_id, item.row_number]));
        expect(projected.totals).toBe(list.totals);
        expect(projected.items).toHaveLength(list.items.length);
        const read = whatTheGridReads(config, projected.items, numbers);
        expect(read).toEqual(whatTheGridReads(config, list.items, numbers));
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

    it(`weigh less than ${share.toString()} of the answer on the volume`, () => {
      const list = answer("volume/nodes_thousand");
      const projected = projectNodes(list, fields);
      expect(JSON.stringify(projected).length).toBeLessThan(JSON.stringify(list).length * share);
    });
  });
}

// The shares the projections weigh on the volume: 0.52 for the estimate, 0.44 for the planning.
holdsWhatTheGridReads("estimate", ESTIMATE_GRID, ESTIMATE_FIELDS, 0.55);
holdsWhatTheGridReads("planning", PLANNING_GRID, PLANNING_FIELDS, 0.47);
