// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The accounts the address of a screen of the administration chooses as authors of its audit columns
 * that its page does not offer — a period that retains no row, a list refused, an account found by a
 * search and the screen opened again —, read by their names (`getUser`), so that the filter names
 * them as everywhere they are cited: a deactivated account by its names, an anonymised one by the
 * neutral label (WF-ADM-0060). At most one read by column, and none when the page offers every
 * account chosen; an account the API does not find (404) stays chosen by its identifier. Any other
 * answer is thrown for the pages of the shell to say.
 */
import { readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import {
  type AuditFilters,
  type AuthorChoice,
  type NamedAuthor,
  unofferedAuthors,
} from "@/components/admin/audit-address";

/** Read by their names the accounts chosen as authors that are not among those offered. */
export async function readChosenAuthors(
  filters: AuditFilters,
  offered: readonly AuthorChoice[],
): Promise<NamedAuthor[]> {
  const client = serverClient();
  const read = await Promise.all(
    unofferedAuthors(filters, offered).map((userId) =>
      readUnlessRefused("getUser", [{ status: 404 }], () =>
        client.GET("/users/{user_id}", { params: { path: { user_id: userId } } }),
      ),
    ),
  );
  return read
    .filter((user) => user !== undefined)
    .map(({ user_id, first_name, last_name }) => ({ user_id, first_name, last_name }));
}
