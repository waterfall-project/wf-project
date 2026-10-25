// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { Locale } from "@/i18n/locale";

import {
  type LagUnit,
  type LinkType,
  parsePredecessors,
  type PredecessorNames,
  predecessorsOf,
  predecessorsText,
  predecessorsValue,
  predecessorsWritten,
} from "./predecessors-entry";

// The names of the two languages, as the catalogues write them (`planningGrid.linkCode`,
// `enums.LagUnit`).
const CODES: Readonly<Record<Locale, Readonly<Record<LinkType, string>>>> = {
  fr: {
    finish_to_start: "FD",
    start_to_start: "DD",
    finish_to_finish: "FF",
    start_to_finish: "DF",
  },
  en: {
    finish_to_start: "FS",
    start_to_start: "SS",
    finish_to_finish: "FF",
    start_to_finish: "SF",
  },
};
const SUFFIXES: Readonly<Record<Locale, Readonly<Record<LagUnit, string>>>> = {
  fr: {
    min: "min",
    h: "h",
    d: "j",
    w: "sem",
    mo: "m",
    emin: "emin",
    eh: "eh",
    ed: "ej",
    ew: "esem",
    emo: "em",
    percent: "%",
  },
  en: {
    min: "min",
    h: "h",
    d: "d",
    w: "wk",
    mo: "mo",
    emin: "emin",
    eh: "eh",
    ed: "ed",
    ew: "ewk",
    emo: "emo",
    percent: "%",
  },
};

// The rows the grid read: row 3 is the task `T3`, and so on; none for any other.
const ROWS = new Map([
  [3, "T3"],
  [5, "T5"],
  [12, "T12"],
]);

/** The names of a language over the rows above. */
function namesOf(locale: Locale): PredecessorNames {
  return {
    code: (link) => CODES[locale][link],
    suffix: (unit) => SUFFIXES[locale][unit],
    resolve: (row) => ROWS.get(row),
  };
}

/** The links a text is read as, without their row numbers' tasks' order of keys: what is sent. */
function sent(text: string, locale: Locale = "fr") {
  const parsed = parsePredecessors(text, locale, namesOf(locale));
  if (!("value" in parsed) || parsed.value === null) {
    return parsed;
  }
  return predecessorsWritten(predecessorsOf(parsed.value) ?? []);
}

describe("the predecessors typed as Microsoft Project writes them", () => {
  it("reads « 3FD+2 j ; 5DD »: a row, its type, its lag in its unit, a link after another [WF-PLA-0030-A]", () => {
    expect(sent("3FD+2 j ; 5DD")).toEqual([
      { predecessor_node_id: "T3", link_type: "finish_to_start", lag: { value: "2", unit: "d" } },
      { predecessor_node_id: "T5", link_type: "start_to_start", lag: { value: "0", unit: "d" } },
    ]);
  });

  it.each([
    { locale: "fr", text: "3FD;3DD;3FF;3DF" },
    { locale: "en", text: "3fs;3SS;3ff;3SF" },
  ] as const)(
    "reads the four types of link by their codes in the language of the interface, $locale [WF-PLA-0030-A]",
    ({ locale, text }) => {
      expect(sent(text, locale)).toEqual(
        (["finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish"] as const).map(
          (link_type) => ({
            predecessor_node_id: "T3",
            link_type,
            lag: { value: "0", unit: "d" },
          }),
        ),
      );
    },
  );

  it("reads a row alone as a plain finish to start, and a lag alone as the lag of that link [WF-PLA-0030-A]", () => {
    expect(sent("12")).toEqual([
      { predecessor_node_id: "T12", link_type: "finish_to_start", lag: { value: "0", unit: "d" } },
    ]);
    expect(sent("12+3 sem")).toEqual([
      { predecessor_node_id: "T12", link_type: "finish_to_start", lag: { value: "3", unit: "w" } },
    ]);
  });

  it.each([
    { text: "3FD-2 j", lag: { value: "-2", unit: "d" } },
    { text: "3-2j", lag: { value: "-2", unit: "d" } },
    { text: "3DD - 1,5 sem", lag: { value: "-1.5", unit: "w" } },
    { text: "3FF+1 m", lag: { value: "1", unit: "mo" } },
    { text: "3FF+1 min", lag: { value: "1", unit: "min" } },
    { text: "3DF+2 ej", lag: { value: "2", unit: "ed" } },
    { text: "3FD+50%", lag: { value: "50", unit: "percent" } },
    { text: "3FD-25 %", lag: { value: "-25", unit: "percent" } },
    { text: "3FD+2", lag: { value: "2", unit: "d" } },
    { text: "3FD-0 j", lag: { value: "0", unit: "d" } },
  ])(
    "reads the lag of « $text » in its unit, a lead when it is negative, a share when it is a percentage [WF-PLA-0030-A]",
    ({ text, lag }) => {
      expect(sent(text)).toEqual([expect.objectContaining({ predecessor_node_id: "T3", lag })]);
    },
  );

  it("reads the suffixes of the language it is typed in: « 1 wk » in English, not in French [WF-PLA-0160-A]", () => {
    expect(sent("3+1 wk", "en")).toEqual([
      expect.objectContaining({ lag: { value: "1", unit: "w" } }),
    ]);
    expect(sent("3+1 wk", "fr")).toEqual({ problem: "notPredecessors" });
    // « m » is a month and « min » a minute whatever the language.
    expect(sent("3+1 m", "en")).toEqual([
      expect.objectContaining({ lag: { value: "1", unit: "mo" } }),
    ]);
  });

  it("empties the predecessors by a blank text, and reads a trailing separator as nothing more", () => {
    expect(parsePredecessors("", "fr", namesOf("fr"))).toEqual({ value: null });
    expect(parsePredecessors(" ; ", "fr", namesOf("fr"))).toEqual({ value: null });
    expect(sent("3;")).toHaveLength(1);
  });

  it.each([
    "FD",
    "3 FD+",
    "3XX",
    "3FD+x j",
    "3FD+2 parsecs",
    "3FD++2",
    "3,5",
    "-3",
    "3FD+-2",
    "3FD 2",
  ])("does not read « %s » as predecessors", (text) => {
    expect(sent(text)).toEqual({ problem: "notPredecessors" });
  });

  it("refuses a row no row read has, saying so [WF-PLA-0030-A]", () => {
    expect(sent("3FD;4")).toEqual({ problem: "unknownRow" });
    expect(sent("0")).toEqual({ problem: "unknownRow" });
  });

  it("goes back to the text it was typed as, in the language, a plain link as its row alone [WF-PLA-0030-A]", () => {
    const value = predecessorsValue([
      {
        predecessor_node_id: "T3",
        predecessor_row_number: 3,
        link_type: "finish_to_start",
        lag: { value: "2", unit: "d" },
      },
      {
        predecessor_node_id: "T5",
        predecessor_row_number: 5,
        link_type: "start_to_start",
        lag: { value: "0", unit: "d" },
      },
      {
        predecessor_node_id: "T12",
        predecessor_row_number: 12,
        link_type: "finish_to_start",
        lag: { value: "0", unit: "d" },
      },
      {
        predecessor_node_id: "T3",
        predecessor_row_number: 3,
        link_type: "start_to_finish",
        lag: { value: "-1.5", unit: "w" },
      },
      {
        predecessor_node_id: "T3",
        predecessor_row_number: 3,
        link_type: "finish_to_finish",
        lag: { value: "50", unit: "percent" },
      },
    ]);
    expect(value).toBeDefined();
    expect(predecessorsText(value ?? "", "fr", namesOf("fr"))).toBe(
      "3FD+2 j; 5DD; 12; 3DF-1,5 sem; 3FF+50 %",
    );
    expect(predecessorsText(value ?? "", "en", namesOf("en"))).toBe(
      "3FS+2 d; 5SS; 12; 3SF-1.5 wk; 3FF+50 %",
    );
    // What the entry starts from reads back as the same links.
    const again = parsePredecessors(
      predecessorsText(value ?? "", "fr", namesOf("fr")),
      "fr",
      namesOf("fr"),
    );
    expect(again).toEqual({ value });
  });

  it("holds no value for no link, and none for a value no entry made", () => {
    expect(predecessorsValue([])).toBeUndefined();
    expect(predecessorsValue(undefined)).toBeUndefined();
    expect(predecessorsOf("garbage")).toBeUndefined();
    expect(predecessorsOf("3|T3|sideways|1|d")).toBeUndefined();
    expect(predecessorsOf("3|T3|finish_to_start|1|fortnight")).toBeUndefined();
    expect(predecessorsOf("3|T3|finish_to_start|1|d|more")).toBeUndefined();
  });
});
