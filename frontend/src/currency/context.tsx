// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The currency of the installation, handed down to every component that shows an amount
 * (WF-REF-0140): the layout reads it once per request (`src/currency/request.ts`), the provider
 * makes it available to the client components below, and `useCurrency` gives it to `formatMoney`.
 * Without a value — no session, or settings out of reach — an amount is shown bare.
 */
"use client";

import { createContext, type ReactNode, useContext } from "react";

const CurrencyContext = createContext<string | undefined>(undefined);

/** Make the currency of the installation available to the components below. */
export function CurrencyProvider({
  currency,
  children,
}: {
  readonly currency: string | undefined;
  readonly children: ReactNode;
}) {
  return <CurrencyContext value={currency}>{children}</CurrencyContext>;
}

/** The ISO 4217 code of the currency amounts are shown in; none when the installation's is unknown. */
export function useCurrency(): string | undefined {
  return useContext(CurrencyContext);
}
