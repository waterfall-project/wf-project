// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The differences of amounts of a comparison, by nature of cost and by sub-project (WF-IHM-0160,
 * US-2350): the budgeted and the re-estimated amounts of the revision read minus those of the base,
 * as `compareRevisions` gives them (`amount_deltas`), on the lines the reading retains — the grid
 * joins nothing and sums nothing (WF-ARC-0020). The estimate and the remaining to commit offer them
 * in the bar of the grid, by a command that opens a dialog: it is reached by the keyboard as by the
 * pointer, and Escape gives the focus back to the command. Each deviation is named by the label the
 * API resolves (#204); the one it leaves out is said unnamed, never replaced by an identifier, and
 * the key `unassigned` is named by the front.
 */
"use client";

import { GitCompareArrows } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { Amount } from "@/components/amount";
import { CELL, ListTable } from "@/components/projects/project-tables";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TableCell, TableRow } from "@/components/ui/table";
import { UNASSIGNED } from "@/navigation/context";

import type { AmountDelta } from "./nodes";

/** The deviations of amounts, by nature of cost and by sub-project, in the order of the server. */
export function AmountDeltasTable({ deltas }: { readonly deltas: readonly AmountDelta[] }) {
  const t = useTranslations("grid.compared.amountDeltas");
  const dimension = useTranslations("enums.RevisionComparison.amount_deltas.dimension");
  const unassigned = useTranslations("enums.Scope")("unassigned");
  if (deltas.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("empty")}</p>;
  }
  return (
    <ListTable
      label={t("title")}
      columns={[t("dimension"), t("key"), t("budgeted"), t("reestimated")]}
    >
      {deltas.map((delta) => (
        <TableRow key={`${delta.dimension}:${delta.key}`}>
          <TableCell className={CELL}>{dimension(delta.dimension)}</TableCell>
          <TableCell className={CELL}>
            {delta.key === UNASSIGNED ? unassigned : (delta.label ?? t("unnamed"))}
          </TableCell>
          <TableCell className={`${CELL} tabular-nums`}>
            <Amount value={delta.budgeted_delta} signed />
          </TableCell>
          <TableCell className={`${CELL} tabular-nums`}>
            <Amount value={delta.reestimated_delta} signed />
          </TableCell>
        </TableRow>
      ))}
    </ListTable>
  );
}

/**
 * The command of the bar of a grid that opens the differences of amounts of its comparison, and the
 * dialog that holds them.
 */
export function AmountDeltasCommand({ deltas }: { readonly deltas: readonly AmountDelta[] }) {
  const t = useTranslations("grid.compared.amountDeltas");
  const [open, setOpen] = useState(false);
  // The dialog has no trigger of Radix to give the focus back to: the command is the one it opened from.
  const command = useRef<HTMLButtonElement>(null);
  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        ref={command}
        aria-haspopup="dialog"
        onClick={() => {
          setOpen(true);
        }}
      >
        <GitCompareArrows aria-hidden="true" />
        {t("command")}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          className="max-w-2xl"
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            command.current?.focus();
          }}
        >
          <DialogHeader>
            <DialogTitle>{t("title")}</DialogTitle>
            <DialogDescription>{t("description")}</DialogDescription>
          </DialogHeader>
          <AmountDeltasTable deltas={deltas} />
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setOpen(false);
              }}
            >
              {t("close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
