// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of a paste, before anything is written (WF-IHM-0050): a modal dialog named for what
 * it does, which says what was pasted and from where, then what the server would write and what
 * it refuses — each row refused named by its place in the block, with its cells as copied and the
 * reason the catalogue gives its code — in one announced region, which holds the waiting first,
 * then the report. A plan that refuses no row is applied on confirmation; one that refuses a row
 * is not, and says so: abandoning it is all it offers. Escape abandons, as the
 * button does, and the focus goes back to the active cell; while the plan is applied, nothing
 * closes the dialog.
 */
"use client";

import { CircleAlert, ClipboardPaste, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { problemMessage } from "@/i18n/problem";

import { headingOf, type PastedBlock, type PastePlan } from "./columns";
import type { Pasting } from "./paste";

/** The rows refused, each with its place in the block, its cells as copied and its reason. */
function Refusals({ plan, block }: { readonly plan: PastePlan; readonly block: PastedBlock }) {
  const t = useTranslations("grid.paste");
  const locale = useLocale();
  const messages = useMessages();
  return (
    <>
      <p className="font-medium text-destructive">
        {t("rejected", { count: plan.rejected.length })}
      </p>
      <ul className="space-y-1">
        {plan.rejected.map((rejection, index) => (
          // A row may be refused twice, same place and same code: the key takes its rank too.
          <li
            key={`${rejection.row.toString()}:${rejection.code}:${index.toString()}`}
            className="space-y-0.5 rounded-md border p-2"
          >
            <p className="flex items-start gap-1.5">
              <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-destructive" />
              {t("rejectedRow", {
                row: rejection.row + 1,
                reason: problemMessage(rejection, { locale, messages }),
              })}
            </p>
            <p className="flex flex-wrap gap-x-3 pl-5.5 text-muted-foreground">
              {(block[rejection.row] ?? []).map((cell, column) => (
                <span key={`${column.toString()}:${cell}`}>{cell}</span>
              ))}
            </p>
          </li>
        ))}
      </ul>
      <p>{t("blocked")}</p>
    </>
  );
}

/**
 * What the server would write and refuse of the block: rows to be written when the plan can be
 * applied; rows merely valid when a refused one blocks it, for the report never promises a write
 * the confirmation cannot do.
 */
function Report({ plan, block }: { readonly plan: PastePlan; readonly block: PastedBlock }) {
  const t = useTranslations("grid.paste");
  const blocked = plan.rejected.length > 0;
  return (
    <>
      <p>{t(blocked ? "validRows" : "accepted", { count: plan.accepted })}</p>
      {blocked ? <Refusals plan={plan} block={block} /> : <p>{t("noneRejected")}</p>}
    </>
  );
}

/** The paste under way, and what to do with it. */
export interface PasteDialogProps {
  readonly pasting: Pasting;
  readonly onApply: () => void;
  readonly onAbandon: () => void;
  /** Give the focus back to the cell the block was pasted on: the dialog has no trigger. */
  readonly onClosed: () => void;
}

/** Show the report of a paste, and apply or abandon it. */
export function PasteDialog({ pasting, onApply, onAbandon, onClosed }: PasteDialogProps) {
  const t = useTranslations("grid");
  const { plan, block, target, applying } = pasting;
  const applicable = plan?.rejected.length === 0 && plan.accepted > 0;
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) {
          onAbandon();
        }
      }}
    >
      <DialogContent
        aria-busy={plan === undefined || applying}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          onClosed();
        }}
      >
        <DialogHeader>
          <DialogTitle>{t("paste.title")}</DialogTitle>
          <DialogDescription>
            {t("paste.block", {
              rows: block.length,
              columns: pasting.width,
              row: target.row,
              column: headingOf(target.column, (key) => t(`columns.${key}`)),
            })}
          </DialogDescription>
        </DialogHeader>
        <div role="status" className="space-y-2 text-sm">
          {plan === undefined ? t("paste.reading") : <Report plan={plan} block={block} />}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" disabled={applying} onClick={onAbandon}>
            <X aria-hidden="true" />
            {t("paste.abandon")}
          </Button>
          {applicable ? (
            <Button type="button" disabled={applying} onClick={onApply}>
              <ClipboardPaste aria-hidden="true" />
              {t("paste.apply")}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
