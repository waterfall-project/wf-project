// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The date a re-estimation that completes a task asks for (WF-RAE-0040, WF-PLA-0130): the entry of a
 * remaining to commit at zero on the last open lines of a task completes it, and the service
 * refuses it without the day (`COMPLETION_DATE_REQUIRED`, `/completed_on`). The grid asks it in a
 * dialog, the day of the workstation proposed, and replays the entry with it; leaving the dialog
 * gives it up, and the refusal is told at the cell.
 */
"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { today } from "@/components/remaining/address";

/** The dialog that asks the date; `onAnswer` gets it, or `null` when the entry is given up. */
export function CompletionDate({ onAnswer }: { readonly onAnswer: (date: string | null) => void }) {
  const t = useTranslations("remainingGrid");
  const id = useId();
  const [date, setDate] = useState(today);
  const [missing, setMissing] = useState(false);
  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!next) {
          onAnswer(null);
        }
      }}
    >
      <DialogContent>
        <form
          noValidate
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (date === "") {
              setMissing(true);
              return;
            }
            onAnswer(date);
          }}
        >
          <DialogHeader>
            <DialogTitle>{t("completionTitle")}</DialogTitle>
            <DialogDescription>{t("completionHint")}</DialogDescription>
          </DialogHeader>
          <Label htmlFor={id}>{t("completionDate")}</Label>
          <Input
            id={id}
            type="date"
            value={date}
            aria-invalid={missing}
            aria-describedby={missing ? `${id}-missing` : undefined}
            onChange={(event) => {
              setDate(event.target.value);
              setMissing(false);
            }}
          />
          {missing ? (
            <p id={`${id}-missing`} role="alert" className="text-xs text-destructive">
              {t("completionRequired")}
            </p>
          ) : null}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                onAnswer(null);
              }}
            >
              <X aria-hidden="true" />
              {t("completionCancel")}
            </Button>
            <Button type="submit">{t("completionConfirm")}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
