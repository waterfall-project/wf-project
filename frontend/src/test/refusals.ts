// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/** The sentence of a refusal, and the refusals of the examples of the contract, for the tests. */
import { expect } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { problemMessage, type ProblemText } from "@/i18n/problem";

import { example } from "./fixtures";

/** The sentence of a refusal in a language. */
export function say(problem: ProblemText, locale: Locale): string {
  return problemMessage(problem, { locale, messages: CATALOGUES[locale] });
}

/**
 * A refusal of an example of the contract, as the test reads it: written as a literal, which the
 * example must match — if the generated example changes, the assertion fails here —, never the
 * example read by a shape assumed for it (#2846).
 */
export function fromExample(name: string, refusal: ProblemText): ProblemText {
  expect(example(name)).toMatchObject(refusal);
  return refusal;
}
