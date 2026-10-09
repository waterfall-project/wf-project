// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The place of a line of actual cost in the tracked scope, shown to be changed (WF-CRE-0030,
 * WF-CRE-0040): the line the address names, its number of document, its amount and whether it is
 * tracked; a tracked line is excluded with the reason the user writes, an excluded one is
 * reinstated, by the command the project lists (`exclude_cost_lines`) — present and available,
 * or unavailable with what it lacks. Once the API has written it, the page reads anew the line and
 * the three totals the server keeps; its refusal is told by the command. The front decides
 * nothing of the scope: the server says whether a line is tracked, and counts the totals.
 */
"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useId, useState } from "react";

import { setCostLineScope } from "@/api/actions/costs";
import { Command } from "@/components/commands/command";
import { commandIcon, PROJECT_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import { rejected } from "@/components/commands/rejection";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatMoney } from "@/i18n/format";

import { ScopeCell, useLineNavigation } from "./cost-cells";
import type { CostRow } from "./cost-grid";

/** The icon of the command, the project's own. */
const ICON = commandIcon(PROJECT_COMMAND_ICONS.exclude_cost_lines);

/** Render the link that stops showing the line: the same screen, its query kept, without it. */
function CloseLine() {
  const t = useTranslations("actualCosts.line");
  const { href, onClick } = useLineNavigation(undefined);
  return (
    <Link
      href={href}
      onClick={onClick}
      scroll={false}
      aria-label={t("close")}
      className={buttonVariants({ variant: "ghost", size: "icon" })}
    >
      <X aria-hidden="true" className="size-4" />
    </Link>
  );
}

/** What the place of a line in the tracked scope shows. */
export interface CostLineScopeProps {
  readonly projectId: string;
  /** The line the address names, as the grid reads it. */
  readonly line: CostRow;
  /** What the project offers of the exclusion of its lines. */
  readonly offer: CommandOffer;
}

/** Render the place of a line in the tracked scope, and the command that changes it. */
export function CostLineScope({ projectId, line, offer }: CostLineScopeProps) {
  const t = useTranslations("actualCosts.line");
  const locale = useLocale();
  const heading = useId();
  const reasonField = useId();
  const [reason, setReason] = useState("");
  const tracked = line.is_in_tracked_scope;
  // The reason written is that of one exclusion: once the server says the line moved, it goes.
  const [written, setWritten] = useState(tracked);
  if (written !== tracked) {
    setWritten(tracked);
    setReason("");
  }
  const change = () =>
    setCostLineScope(projectId, line.cost_line_id, {
      is_in_tracked_scope: !tracked,
      reason: tracked && reason.trim() !== "" ? reason.trim() : null,
    }).catch(rejected);
  return (
    <section aria-labelledby={heading} className="space-y-2 rounded-md border p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 id={heading} className="font-medium">
          {t("title", { document: line.document_number })}
        </h2>
        <CloseLine />
      </div>
      <p className="flex flex-wrap items-center gap-2">
        <span className="tabular-nums">{formatMoney(line.amount, locale)}</span>
        <ScopeCell tracked={tracked} />
      </p>
      {tracked ? (
        <div className="space-y-1">
          <Label htmlFor={reasonField} className="text-muted-foreground">
            {t("reason")}
          </Label>
          <Input
            id={reasonField}
            value={reason}
            onChange={(event) => {
              setReason(event.target.value);
            }}
          />
        </div>
      ) : (
        <p className="text-muted-foreground">
          {line.excluded_reason == null
            ? t("excludedWithoutReason")
            : t("excludedBecause", { reason: line.excluded_reason })}
        </p>
      )}
      <Command
        offer={offer}
        label={tracked ? t("exclude") : t("reinstate")}
        icon={ICON}
        action={change}
      />
    </section>
  );
}
