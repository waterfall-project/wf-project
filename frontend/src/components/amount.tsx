// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * An amount as the interface writes it: in the language of the request, with the currency of the
 * installation (WF-REF-0140). A component of the client, so that a screen of the server, which
 * cannot read the currency from the context, still shows it.
 */
"use client";

import { useLocale } from "next-intl";

import { useCurrency } from "@/currency/context";
import { formatMoney } from "@/i18n/format";
import type { components } from "@/api/generated/schema";

/** An amount, `Money` of the contract, with its currency. */
export function Amount({ value }: { readonly value: components["schemas"]["Money"] }) {
  return formatMoney(value, useLocale(), useCurrency());
}
