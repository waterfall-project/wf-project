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
  type Node,
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

/** An answer of `listNodes`, among the examples of the contract. */
function answer(name: string): NodeList {
  return example(name) as NodeList;
}

/**
 * Everything a grid reads of its rows, row by row: the key, the number, the level, how the label
 * stands out, the value of each column — that it formats, sorts and totals —, and the markup of
 * the icon of the nature and of each cell its column renders, the predecessors named by the row
 * numbers of the answer.
 */
function whatTheGridReads<Row>(
  config: GridConfig<Row, NodeSortColumn, NodeTotals>,
  rows: readonly Row[],
  numbers: ReadonlyMap<string, number>,
) {
  const values = rows.map((row) => [
    config.rowKey(row),
    config.rowNumber?.(row),
    config.tree?.level(row),
    config.tree?.emphasis?.(row),
    ...config.columns.map((column) => column.value(row)),
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
 * and weigh far less.
 */
function holdsWhatTheGridReads<
  N extends keyof Node,
  T extends keyof TaskFacet,
  L extends keyof EstimateLineFacet,
>(
  grid: string,
  config: GridConfig<NodeRow<N, T, L>, NodeSortColumn, NodeTotals>,
  fields: NodeFields<N, T, L>,
) {
  describe(`the rows the page hands the grid of the ${grid}`, () => {
    it.each(ANSWERS)(
      "keep all the grid reads of the answer %s, the totals as they are",
      (name) => {
        const list = answer(name);
        const projected = projectNodes(list, fields);
        const numbers = new Map(list.items.map((node) => [node.node_id, node.row_number]));
        expect(projected.totals).toBe(list.totals);
        expect(projected.items).toHaveLength(list.items.length);
        const read = whatTheGridReads(config, projected.items, numbers);
        expect(read).toEqual(whatTheGridReads(config, list.items, numbers));
        expect(read.markup).toContain('role="img"');
      },
      VOLUME_TIMEOUT,
    );

    it("leave out what the grid does not read, and weigh less than three fifths of the answer", () => {
      const list = answer("volume/nodes_thousand");
      const projected = projectNodes(list, fields);
      const task = new Set<string>(["label", "is_summary", "is_milestone", ...fields.task]);
      const line = new Set<string>(["label", "is_computed", "resource_role_id", ...fields.line]);
      for (const row of projected.items) {
        expect(row).not.toHaveProperty("lineage_id");
        expect(row).not.toHaveProperty("parent_id");
        expect(Object.keys(row.task ?? {}).filter((key) => !task.has(key))).toEqual([]);
        expect(Object.keys(row.estimate_line ?? {}).filter((key) => !line.has(key))).toEqual([]);
      }
      expect(JSON.stringify(projected).length).toBeLessThan((JSON.stringify(list).length * 3) / 5);
    });

    it("keep what an entry sends back and what the server computes, a field left out staying out", () => {
      const list = answer("nodes");
      for (const [index, row] of projectNodes(list, fields).items.entries()) {
        const node = list.items[index];
        expect(row).toMatchObject({
          node_id: node?.node_id,
          lock_version: node?.lock_version,
          computed_fields: node?.computed_fields,
          row_number: node?.row_number,
        });
        expect(Object.keys(row).filter((key) => node === undefined || !(key in node))).toEqual([]);
      }
    });
  });
}

holdsWhatTheGridReads("estimate", ESTIMATE_GRID, ESTIMATE_FIELDS);
holdsWhatTheGridReads("planning", PLANNING_GRID, PLANNING_FIELDS);
