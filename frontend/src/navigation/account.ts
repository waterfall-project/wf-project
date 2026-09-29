// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pages of the account of the user, which the menu of the account leads to: the account
 * itself — its details and its display preferences —, the change of its password, the change of
 * its avatar (US-0320, `src/app/account/`).
 */

/** A page of the account. */
export type AccountPage = "account" | "password" | "avatar";

/** A page of the account, its route, and the key of its name in the catalogues. */
export interface AccountEntry {
  readonly page: AccountPage;
  readonly route: string;
  readonly label: `accountMenu.${AccountPage}`;
}

/** The pages of the account, in the order the menu offers them. */
export const ACCOUNT_PAGES: readonly AccountEntry[] = [
  { page: "account", route: "/account", label: "accountMenu.account" },
  { page: "password", route: "/account/password", label: "accountMenu.password" },
  { page: "avatar", route: "/account/avatar", label: "accountMenu.avatar" },
];

/** The page of the account a path leads to, or `undefined` when it leads to none. */
export function findAccountPage(pathname: string): AccountEntry | undefined {
  return ACCOUNT_PAGES.find((entry) => entry.route === pathname);
}
