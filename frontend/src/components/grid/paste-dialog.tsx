// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of a paste, before anything is written (WF-IHM-0050): a modal dialog named for what
 * it does, which says what was pasted and from where, then what the server would write and what
 * it refuses — each row refused named by its place in the block, with its cells as copied and the
 * reason the catalogue gives its code — in one announced region, which holds the waiting first,
 * then the report. A plan is applied on confirmation as long as it writes a row: one that refuses
 * rows says that the valid ones alone will be written (EP-14/L42q); one that writes none offers
 * only to abandon it. Escape abandons, as the button does, and the focus goes back to the active
 * cell; while the plan is applied, nothing closes the dialog. Once applied, what the server did not
 * write — the refusals of the preview, and those it adds judging the accepted rows again — is told
 * above the grid with the cell the block was pasted from and the number of rows written, the
 * refusals in a region of their own whose height is bounded, until the user dismisses it
 * (`PasteAppliedNotice`).
 */
"use client";

import { CircleAlert, ClipboardPaste, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { useId } from "react";

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

import { headingOf, type PastedBlock, type PastePlan, type PasteRejection } from "./columns";
import type { Pasting, PasteReport } from "./paste";

/** How many rows of the block are refused: a row refused for several cells counts once. */
function refusedRows(rejected: readonly PasteRejection[]): number {
  return new Set(rejected.map((rejection) => rejection.row)).size;
}

/** The rows refused, each with its place in the block, its cells as copied and its reason. */
function Refusals({
  rejected,
  block,
}: {
  readonly rejected: readonly PasteRejection[];
  readonly block: PastedBlock;
}) {
  const t = useTranslations("grid.paste");
  const locale = useLocale();
  const messages = useMessages();
  return (
    <>
      <p className="font-medium text-destructive">
        {t("rejected", { count: refusedRows(rejected) })}
      </p>
      <ul className="space-y-1">
        {rejected.map((rejection, index) => (
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
    </>
  );
}

/**
 * What the server would write and refuse of the block: the rows to be written, the rows refused,
 * and, when it refuses some and writes others, that the confirmation writes the valid rows alone.
 */
function Report({ plan, block }: { readonly plan: PastePlan; readonly block: PastedBlock }) {
  const t = useTranslations("grid.paste");
  const refused = plan.rejected.length > 0;
  return (
    <>
      <p>{t("accepted", { count: plan.accepted })}</p>
      {refused ? <Refusals rejected={plan.rejected} block={block} /> : <p>{t("noneRejected")}</p>}
      {refused && plan.accepted > 0 ? <p>{t("partial")}</p> : null}
    </>
  );
}

/** What a paste applied did not write, and how to forget it. */
export interface PasteAppliedNoticeProps {
  /** What the last paste applied did not write; none when it wrote every row, or before any. */
  readonly applied: PasteReport | undefined;
  /** Forget it. */
  readonly onClear: () => void;
  /** Once dismissed: where the focus goes back, which the notice took with its button. */
  readonly onDismissed: () => void;
}

/**
 * Tell, once a paste is applied, where the block was pasted from, how many rows the server wrote and
 * the rows it did not, each with its place in the block, its cells and its reason — those the
 * confirmation refused judging the accepted rows again among them —, until the user dismisses it;
 * nothing when every row was written. The refusals are a region of their own, named and reached by
 * the keyboard, whose height is bounded: they scroll, and the grid under them stays in the window,
 * the sentence and the command to dismiss staying out of the scroll.
 */
export function PasteAppliedNotice({ applied, onClear, onDismissed }: PasteAppliedNoticeProps) {
  const t = useTranslations("grid");
  const outcome = useTranslations("outcome");
  const told = useId();
  if (applied === undefined) {
    return null;
  }
  const { target } = applied;
  return (
    <div role="alert" className="space-y-1 text-sm">
      <p id={told} className="font-medium">
        {t("paste.appliedFrom", {
          row: target.row,
          column: headingOf(target.column, (key) => t(`columns.${key}`)),
          count: applied.written,
        })}
      </p>
      {/* However many rows are refused, the grid stays in the window: the list scrolls (#163). */}
      <section
        aria-label={t("paste.refusedRows")}
        tabIndex={0}
        className="max-h-40 space-y-1 overflow-y-auto rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Refusals rejected={applied.rejected} block={applied.block} />
      </section>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-describedby={told}
        onClick={() => {
          onClear();
          onDismissed();
        }}
      >
        <X aria-hidden="true" />
        {outcome("dismiss")}
      </Button>
    </div>
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
  const applicable = plan !== undefined && plan.accepted > 0;
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
