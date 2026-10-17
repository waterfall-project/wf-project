// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The one rendering of the neutral label of an anonymised account (WF-ADM-0060), wherever a cell
 * names an account the API gives no name: in the grid of the accounts, the author and the object of
 * an inscription of the journal, the author of a transition. Muted, as a value the screen says in
 * place of one the account no longer has, and marked `data-anonymized` so that every screen shows
 * it alike. An option of a `<select>` holds text only: it takes `useAccountNaming().kept(null)`.
 *
 * Neither server nor client: a page of the server and a component of the browser render it alike.
 */
import { useAccountNaming } from "./account-name";

/** The neutral label of an anonymised account. */
export function AnonymizedName() {
  const naming = useAccountNaming();
  return (
    <span className="text-muted-foreground" data-anonymized="">
      {naming.kept(null)}
    </span>
  );
}

/** A name the API kept of an account, or the neutral label when it is null, the account anonymised. */
export function KeptName({ name }: { readonly name: string | null }) {
  return name ?? <AnonymizedName />;
}
