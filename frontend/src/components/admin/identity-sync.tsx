// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading of the accounts of the identity provider, on the screen of the accounts (US-0370,
 * WF-ADM-0070): the report of the last reading that ended (`getLatestIdentitySync`), asked by an
 * administrator or by the platform at its interval — the accounts created, updated, deactivated,
 * those whose identity it gave back to the provider, the local accounts it removes from it, and what
 * it left as it was, each with its motive, a sentence of the catalogue of the codes of error —; and,
 * for a session that may modify the accounts (`users.write`), the command that asks a new one.
 *
 * The reading is the worker's (WF-ARC-0090): the command gives the hand back as soon as the task is
 * queued, and hands it over to the tracker of the shell, which follows it to its end and announces
 * it, then offers to read the screen anew, where its report shows — the tracker never reloads by
 * itself. A refusal of the command is told under it (`OutcomeNotice`).
 *
 * An account of Waterfall left as it was is named as it reads now, the neutral label for one
 * anonymised since (WF-ADM-0060, #920); a person of the provider without an account by her name and
 * her identifier there, her address when she has one (#918) — save one whose address an account
 * holds, by her identifier and the account as it reads now (#920). Every figure as the API gives it.
 * Every prop is data (défaut n° 12 de `typescript.md`).
 */
"use client";

import { ChevronDown, ChevronRight, UserRoundSearch } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useId, useState, useTransition } from "react";

import { startIdentitySync } from "@/api/actions/users";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { useAccountNaming } from "@/components/account/account-name";
import { AnonymizedName } from "@/components/account/anonymized-name";
import { useHeldCommand } from "@/components/commands/held";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { LocalTime } from "@/components/local-time";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";

/** The report of a reading of the accounts, as the contract gives it. */
export type IdentitySyncReport = components["schemas"]["IdentitySyncReport"];

/** What a reading left as it was: an account of Waterfall, or a person of the provider. */
type Skipped = components["schemas"]["IdentitySyncSkipped"];

/** The counts of a report, each said by a sentence of the catalogue. */
const COUNTS = ["created", "updated", "deactivated", "restored"] as const;

/**
 * An account of Waterfall as it reads now — the one left as it was, or the one that holds the
 * address of a person of the provider —: the neutral label for one anonymised since (WF-ADM-0060).
 */
function AccountName({ entry }: { readonly entry: Skipped }) {
  const naming = useAccountNaming();
  return entry.first_name === null || entry.last_name === null ? (
    <AnonymizedName />
  ) : (
    naming.person(entry)
  );
}

/** A person of the provider by the name it holds of her, and says so when it holds none. */
function PersonName({ entry }: { readonly entry: Skipped }) {
  const t = useTranslations();
  const { first_name: first, last_name: last } = entry;
  if (!first && !last) {
    return t("admin.identitySync.unnamed");
  }
  return t("accountName.full", { first: first ?? "", last: last ?? "" });
}

/**
 * One thing the reading left as it was: who, what, how the provider knows it, and why. A person whose
 * address an account of Waterfall holds (`ALREADY_EXISTS`) keeps nothing of her own but her
 * identifier at the provider: the entry names the account that holds it, as it reads now, and only
 * her identifier when none held it any more (#920).
 */
function SkippedEntry({ entry }: { readonly entry: Skipped }) {
  const t = useTranslations();
  const held = entry.kind === "person" && entry.code === "ALREADY_EXISTS";
  let who: ReactNode = null;
  let address: ReactNode = null;
  if (held) {
    address =
      entry.user_id === null
        ? null
        : t.rich("admin.identitySync.carrier", { name: () => <AccountName entry={entry} /> });
  } else {
    who = entry.kind === "account" ? <AccountName entry={entry} /> : <PersonName entry={entry} />;
    address = entry.email === null ? null : t("admin.identitySync.address", { email: entry.email });
  }
  return (
    <li className="space-y-0.5">
      <p className="flex flex-wrap gap-x-2">
        {who === null ? null : <span className="font-medium">{who}</span>}
        <span className="text-muted-foreground">
          {t(`enums.IdentitySyncSkipped.kind.${entry.kind}`)}
        </span>
      </p>
      {address === null ? null : <p className="text-muted-foreground">{address}</p>}
      {entry.subject === null ? null : (
        <p className="text-muted-foreground">
          {t("admin.identitySync.subject", { subject: entry.subject })}
        </p>
      )}
      <p>{t(`errors.${entry.code}`)}</p>
    </li>
  );
}

/** What the reading left as it was, and the local accounts it removes from the provider. */
function Details({ id, report }: { readonly id: string; readonly report: IdentitySyncReport }) {
  const t = useTranslations("admin.identitySync");
  return (
    <div
      id={id}
      role="region"
      aria-label={t("details")}
      // Scrolled within, so that the table keeps its room: reachable from the keyboard.
      tabIndex={0}
      className="max-h-60 space-y-3 overflow-y-auto rounded-md border p-3"
    >
      <section aria-label={t("skippedTitle")} className="space-y-1">
        <h3 className="font-medium">{t("skippedTitle")}</h3>
        {report.skipped.length === 0 ? (
          <p className="text-muted-foreground">{t("noneSkipped")}</p>
        ) : (
          <ul className="space-y-2">
            {report.skipped.map((entry, index) => (
              <SkippedEntry key={entry.subject ?? entry.user_id ?? index} entry={entry} />
            ))}
          </ul>
        )}
      </section>
      <section aria-label={t("removedTitle")} className="space-y-1">
        <h3 className="font-medium">{t("removedTitle")}</h3>
        {report.removed.length === 0 ? (
          <p className="text-muted-foreground">{t("noneRemoved")}</p>
        ) : (
          <ul>
            {report.removed.map((email) => (
              <li key={email}>{email}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

/** The report of the last reading: when it ended, what it did, and, on demand, what it left. */
function Report({ report }: { readonly report: IdentitySyncReport }) {
  const t = useTranslations("admin.identitySync");
  const details = useId();
  const [open, setOpen] = useState(false);
  return (
    <div className="space-y-2">
      <p>{t.rich("finished", { time: () => <LocalTime value={report.finished_at} /> })}</p>
      <ul className="flex flex-wrap gap-x-4 gap-y-1">
        {COUNTS.map((count) => (
          <li key={count}>{t(count, { count: report[count] })}</li>
        ))}
        <li>{t("removed", { count: report.removed.length })}</li>
        <li>{t("skipped", { count: report.skipped.length })}</li>
      </ul>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-expanded={open}
        aria-controls={open ? details : undefined}
        onClick={() => {
          setOpen(!open);
        }}
      >
        {open ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
        {t("details")}
      </Button>
      {open ? <Details id={details} report={report} /> : null}
    </div>
  );
}

/** Ask a reading of the accounts, and hand its task over to the tracker. */
function StartIdentitySync() {
  const t = useTranslations("admin.identitySync");
  const track = useTrackTask();
  const held = useHeldCommand();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const start = () => {
    if (pending) {
      return;
    }
    startTransition(async () => {
      const result = await held(startIdentitySync());
      if (result.kind === "done") {
        setOutcome(undefined);
        track(result.data, { command: startIdentitySync });
      } else {
        setOutcome(result);
      }
    });
  };
  return (
    <div className="space-y-2">
      <Button type="button" variant="outline" size="sm" aria-busy={pending} onClick={start}>
        <UserRoundSearch aria-hidden="true" />
        {t("start")}
      </Button>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </div>
  );
}

/**
 * The report of the last reading of the accounts — none until one has ended —, and the command that
 * asks a new one, to a session that may modify the accounts.
 */
export function IdentitySync({
  report,
  startable,
}: {
  /** The report of the last reading that ended; none yet. */
  readonly report: IdentitySyncReport | undefined;
  /** Whether the session may modify the accounts (`platformOffer`): the command is offered. */
  readonly startable: boolean;
}) {
  const t = useTranslations("admin.identitySync");
  return (
    <section aria-label={t("title")} className="shrink-0 space-y-2 text-sm">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 className="text-base font-semibold">{t("title")}</h2>
        {startable ? <StartIdentitySync /> : null}
      </div>
      {report === undefined ? (
        <p className="text-muted-foreground">{t("none")}</p>
      ) : (
        <Report report={report} />
      )}
    </section>
  );
}
