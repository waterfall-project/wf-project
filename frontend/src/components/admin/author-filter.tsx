// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a table of the administration on the author of an audit column — who created its
 * rows, who last modified them (WF-DAT-0070, WF-IHM-0130, #936) —: a choice among any account, the
 * platform — an automatic process, by its own label —, and the accounts offered, each by the name its
 * rows keep of it, an account deactivated since still named and an anonymised one by the neutral
 * label (WF-ADM-0060). The accounts offered are those the page gives: the authors of the roles, all of
 * them; the authors of the page of the accounts shown — and, there, those a search finds among the
 * accounts (`findAccounts`, `listUsers` searched), the contract having no list of the authors. A
 * choice only changes the address, under the names of the contract — the account, or the kind of
 * author —, back to the first page (`ChoiceFilter`). An account chosen that the page does not offer
 * is named as the page read it (`named`), never by its identifier.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useRef, useState } from "react";

import { findAccounts } from "@/api/actions/users";
import type { Outcome } from "@/api/problem";
import { useAccountNaming } from "@/components/account/account-name";
import { rejected } from "@/components/commands/rejection";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { ChoiceFilter } from "@/components/grid/choice-filter";
import { SEARCH_LENGTH } from "@/components/grid/query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import type { Author, AuthorChoice, AuthorNames, NamedAuthor } from "./audit-address";

/** What the filter of an author shows. */
export interface AuthorFilterProps {
  /** The heading of the column it filters: « Créé par », « Modifié par ». */
  readonly label: string;
  /** The parameters of the address it writes, as the contract names them. */
  readonly names: AuthorNames;
  /** The author the address filters on; none, any. */
  readonly chosen: Author;
  /** The accounts offered, in the order the page gives them. */
  readonly offered: readonly AuthorChoice[];
  /**
   * The accounts the address chooses that the page does not offer, by the names it read of them: the
   * one chosen is named so, never by its identifier (WF-ADM-0060).
   */
  readonly named: readonly NamedAuthor[];
  /** Whether other accounts may be found by a search of the accounts. */
  readonly searchable: boolean;
  /** The parameter of the page of a list the server pages, which a choice takes back to its first. */
  readonly page?: string | undefined;
}

/** Render the filter of a table on the author of one of its audit columns. */
export function AuthorFilter({
  label,
  names,
  chosen,
  offered,
  named,
  searchable,
  page,
}: AuthorFilterProps) {
  const t = useTranslations();
  const naming = useAccountNaming();
  // The accounts the last search found, already named: they join those the page offers.
  const [found, setFound] = useState<readonly { id: string; name: string }[]>([]);
  const offeredIds = new Set(offered.map((author) => author.id));
  const accounts = [
    ...offered.map((author) => ({ value: author.id, text: naming.kept(author.name) })),
    ...found
      .filter((account) => !offeredIds.has(account.id))
      .map((account) => ({ value: account.id, text: account.name })),
  ];
  // The account chosen, if the page does not offer it: by its names, as everywhere it is cited.
  const unoffered = named.find((account) => account.user_id === chosen.user);
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-2">
      <ChoiceFilter
        name={names.user}
        label={label}
        every={t("admin.audit.everyAuthor")}
        choices={[
          { value: "user", text: t("admin.audit.anyAccount"), name: names.kind },
          { value: "platform", text: t("enums.AuditActorKind.platform"), name: names.kind },
          ...accounts,
        ]}
        chosen={chosen.user ?? chosen.kind}
        unknown={unoffered === undefined ? undefined : naming.person(unoffered)}
        page={page}
      />
      {searchable ? (
        <AuthorSearch
          column={label}
          onFound={(accounts) => {
            setFound(
              accounts.map((account) => ({ id: account.user_id, name: naming.person(account) })),
            );
          }}
        />
      ) : null}
    </div>
  );
}

/** The accounts a search finds, by their identifiers and their names. */
type Found = readonly NamedAuthor[];

/**
 * The search of the accounts that may be chosen as the author of a column: a text sent to the server,
 * which finds the accounts on their names and address; the last search sent alone answers, an older
 * one arriving after it said nothing (défaut n° 1 de `typescript.md`). How many it found is said, a
 * refusal told by the catalogue of the codes of error.
 */
function AuthorSearch({
  column,
  onFound,
}: {
  readonly column: string;
  readonly onFound: (accounts: Found) => void;
}) {
  const t = useTranslations("admin.audit");
  const field = useId();
  const [text, setText] = useState("");
  const [told, setTold] = useState<number | undefined>(undefined);
  const [failure, setFailure] = useState<Outcome<unknown> | undefined>(undefined);
  // Busy from the search sent last to its answer, and lifted in the very update that tells it — not a
  // transition, whose end would wait for every other async action of the page (#1484).
  const [busy, setBusy] = useState(false);
  // The search last sent: an answer to another is not shown.
  const sent = useRef(0);
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    const search = text.trim();
    if (search === "") {
      return;
    }
    sent.current += 1;
    const mine = sent.current;
    setBusy(true);
    void findAccounts(search)
      .catch(rejected)
      .then((outcome) => {
        if (mine !== sent.current) {
          return;
        }
        if (outcome.kind === "done") {
          setFailure(undefined);
          setTold(outcome.data.length);
          onFound(outcome.data);
        } else {
          setTold(undefined);
          setFailure(outcome);
        }
        setBusy(false);
      });
  };
  return (
    <form
      aria-label={t("find", { column })}
      onSubmit={submit}
      className="flex flex-wrap items-center gap-2 text-sm"
    >
      <Label htmlFor={field} className="sr-only">
        {t("find", { column })}
      </Label>
      <Input
        id={field}
        type="search"
        value={text}
        maxLength={SEARCH_LENGTH}
        onChange={(event) => {
          setText(event.target.value);
        }}
        className="h-8 w-44"
      />
      <Button type="submit" size="sm" variant="outline" disabled={busy}>
        <Search aria-hidden="true" className="size-4" />
        {t("findButton")}
      </Button>
      <span role="status" className="text-muted-foreground">
        {told === undefined ? null : t("found", { count: told, column })}
      </span>
      <OutcomeNotice
        outcome={failure}
        onClear={() => {
          setFailure(undefined);
        }}
      />
    </form>
  );
}
