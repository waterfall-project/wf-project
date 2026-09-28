// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The catalogues of texts, one per offered language: `messages/fr.json`, the reference, and
 * `messages/en.json`, its twin. next-intl is typed by the reference (`next-intl.d.ts`): a key
 * the code uses and the French catalogue lacks fails `make typecheck-front`, and the English
 * one must have every key of the French one to be assigned here.
 */
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";

import type { Locale } from "./locale";

/** The texts of the interface, shaped as the reference catalogue. */
export type Catalogue = typeof fr;

/** The catalogue of each offered language. */
export const CATALOGUES: Readonly<Record<Locale, Catalogue>> = { fr, en };
