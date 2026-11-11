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
 * author —, back to the first page, at once. The list has its search inside (`CheckMenu`): a text
 * typed filters the accounts offered, and, where the accounts may be searched, is sent to the
 * server once the typing pauses, the accounts it finds joining the list — no button to press
 * (#2916). An account chosen that the page does not offer
 * is named as the page read it (`named`), never by its identifier.
 *
 * Every prop is data — the texts are given translated —, never a function: a server component
 * hands it over (défaut n° 12 de `typescript.md`).
 */
"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useOptimistic, useRef, useState, useTransition } from "react";

import { findAccounts } from "@/api/actions/users";
import type { Outcome } from "@/api/problem";
import { useAccountNaming } from "@/components/account/account-name";
import { rejected } from "@/components/commands/rejection";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { CheckMenu } from "@/components/grid/check-menu";
import { filterHref } from "@/components/grid/filters";
import { usePendingAddress } from "@/components/grid/pending-address";

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
  const pathname = usePathname();
  const { request } = usePendingAddress();
  // The accounts the last search found, already named: they join those the page offers.
  const [found, setFound] = useState<readonly { id: string; name: string }[]>([]);
  const [told, setTold] = useState<number | undefined>(undefined);
  const [failure, setFailure] = useState<Outcome<unknown> | undefined>(undefined);
  const offeredIds = new Set(offered.map((author) => author.id));
  const accounts = [
    ...offered.map((author) => ({ value: author.id, text: naming.kept(author.name) })),
    ...found
      .filter((account) => !offeredIds.has(account.id))
      .map((account) => ({ value: account.id, text: account.name, found: true })),
  ];
  // The account chosen, if the page does not offer it: by its names, as everywhere it is cited.
  const unoffered = named.find((account) => account.user_id === chosen.user);
  const value = chosen.user ?? chosen.kind ?? "";
  const options = [
    { value: "user", text: t("admin.audit.anyAccount") },
    { value: "platform", text: t("enums.AuditActorKind.platform") },
    ...accounts,
    ...(value === "" ||
    ["user", "platform"].includes(value) ||
    accounts.some((account) => account.value === value)
      ? []
      : [{ value, text: unoffered === undefined ? value : naming.person(unoffered) }]),
  ];
  const [shown, show] = useOptimistic(value);
  const [, startTransition] = useTransition();
  // The search of the server, one at a time: an answer for a text typed since is not told (défaut n° 1).
  const latest = useRef("");
  const query = useCallback(
    (text: string) => {
      latest.current = text;
      if (text === "") {
        // The search is cleared: what it found goes with it.
        setTold(undefined);
        setFound([]);
        setFailure(undefined);
        return;
      }
      void findAccounts(text)
        .catch(rejected)
        .then((outcome) => {
          if (latest.current !== text) {
            return;
          }
          if (outcome.kind === "done") {
            setFailure(undefined);
            setTold(outcome.data.length);
            setFound(
              outcome.data.map((account) => ({
                id: account.user_id,
                name: naming.person(account),
              })),
            );
          } else {
            setTold(undefined);
            setFailure(outcome);
          }
        });
    },
    [naming],
  );
  const footer =
    searchable && (told !== undefined || failure !== undefined) ? (
      <div className="flex flex-col gap-1">
        <span role="status" className="px-1 text-xs text-muted-foreground">
          {told === undefined ? null : t("admin.audit.found", { count: told, column: label })}
        </span>
        <OutcomeNotice
          outcome={failure}
          onClear={() => {
            setFailure(undefined);
          }}
        />
      </div>
    ) : null;
  return (
    <CheckMenu
      label={label}
      every={t("admin.audit.everyAuthor")}
      multiple={false}
      searchable
      options={options}
      chosen={shown === "" ? [] : [shown]}
      onQuery={searchable ? query : undefined}
      footer={footer}
      onChange={([next]) => {
        const picked = next ?? "";
        const written = picked === "user" || picked === "platform" ? names.kind : names.user;
        startTransition(() => {
          show(picked);
          request((query) =>
            filterHref(pathname, query, written, picked, [
              ...(page === undefined ? [] : [page]),
              ...[names.user, names.kind].filter((each) => each !== written),
            ]),
          );
        });
      }}
    />
  );
}
