// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The name an account shows wherever a screen names it: its first and last names, or the name the
 * API kept of it — in the audit columns of an object, in an inscription of the journal —, and, for
 * an anonymised account, the neutral label of the catalogue (WF-ADM-0060). The API gives the names
 * of an anonymised account null and no sentence in their place (WF-ARC-0110, #832): the front says
 * it, and never shows a name or an address the account no longer has.
 *
 * Neither server nor client: a page of the server and a component of the browser name alike.
 */
import { useTranslations } from "next-intl";
import { useMemo } from "react";

import type { NamedAccount } from "./initials";

/** How a screen names an account. */
export interface AccountNaming {
  /** An account by its first and last names; the neutral label for an anonymised one. */
  readonly person: (account: NamedAccount) => string;
  /** A name the API kept of an account; the neutral label when null, the account anonymised. */
  readonly kept: (name: string | null) => string;
}

/**
 * Name the accounts in the language of the screen — the same naming from one render to the next, so
 * that a configuration that names an account in its callbacks is not built anew at each.
 */
export function useAccountNaming(): AccountNaming {
  const t = useTranslations();
  return useMemo(() => {
    const neutral = () => t("accountName.anonymized");
    return {
      person: ({ first_name: first, last_name: last }) =>
        first === null || last === null ? neutral() : t("accountName.full", { first, last }),
      kept: (name) => name ?? neutral(),
    };
  }, [t]);
}
