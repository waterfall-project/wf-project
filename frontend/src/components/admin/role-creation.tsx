// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dialog that creates an access role (US-0380, US-2100): its label, which the contract bounds,
 * and nothing else — its permissions are written in the matrix. It opens from « Nouveau rôle », the
 * principal command of the card of the roles (`CreateRole`, `role-commands.tsx`). A label left blank
 * is refused at its field as the entry of the grid refuses it (`parsedEntry`), nothing asked, the
 * field taking the focus; the label the server refuses (422, `/label`) is said at its field too,
 * which takes the focus, the dialog staying open to be corrected; any other refusal is told above
 * the table, on the reading the form was sent from (`useListReport`). The dialog may be closed
 * meanwhile: a creation answered is said all the same, and a refusal told above the table.
 */
"use client";

import { Plus, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState } from "react";

import { createAccessRole } from "@/api/actions/access-roles";
import type { components } from "@/api/generated/schema";
import { useHeldCommand } from "@/components/commands/held";
import { useNoteRefusal } from "@/components/commands/outcome-notice";
import { parsedEntry } from "@/components/grid/cell-values";
import { useListReading } from "@/components/reference/list-reading";
import { useListReport } from "@/components/reference/reactivation";
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
import { problemMessage } from "@/i18n/problem";

import { LABEL_LENGTH } from "./role-address";

type AccessRole = components["schemas"]["AccessRole"];

/** Render the dialog that creates an access role, open as long as it is rendered. */
export function RoleCreation({
  onCreated,
  onClose,
  onClosed,
}: {
  /** Take the role created, the dialog open or closed. */
  readonly onCreated: (role: AccessRole) => void;
  readonly onClose: () => void;
  /** Give the focus back where the dialog was opened from, once it has closed. */
  readonly onClosed: () => void;
}) {
  const t = useTranslations("admin.accessRoles");
  const form = useTranslations("reference.form");
  const columns = useTranslations("grid.columns");
  const locale = useLocale();
  const messages = useMessages();
  const list = useListReport();
  // The list holds the navigations while the creation answers, its refusal told above it or at the
  // field (#688, #889).
  const own = useHeldCommand();
  const held = list?.held ?? own;
  const noteRefusal = useNoteRefusal();
  const [label, setLabel] = useState("");
  const [refused, setRefused] = useState<string>();
  // Busy from the press to the answer, and lifted in the very update that tells it — not a transition,
  // whose end would wait for every other write of the table under way (#1484).
  const [busy, setBusy] = useState(false);
  // A write of the list lost once sent: the list is read anew, and this waits until it is back (US-2240).
  const reading = useListReading();
  // Asked anew at each refusal: the field takes the focus after the commit that says its refusal,
  // described by it as it is heard (#1484).
  const [focused, setFocused] = useState<object>();
  const input = useRef<HTMLInputElement>(null);
  const field = useId();
  // Whether the dialog is still on the screen: gone, it tells nothing, and the list must.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (focused !== undefined) {
      input.current?.focus();
    }
  }, [focused]);

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy || reading) {
      return;
    }
    const parsed = parsedEntry({ type: "text", maxLength: LABEL_LENGTH }, label, locale);
    if ("problem" in parsed) {
      const code = parsed.problem === "required" ? "VALUE_REQUIRED" : "VALUE_TOO_LONG";
      setRefused(problemMessage({ code }, { locale, messages }));
      setFocused({});
      return;
    }
    // The reading the role is created from: its refusal is told on it alone.
    const generation = list?.generation ?? 0;
    const asked = label;
    setRefused(undefined);
    setBusy(true);
    // Whether the field tells the refusal: the list, read anew meanwhile, is not asked to tell it
    // too, the bar of the shell neither — the field is on the form, whatever the list shows.
    // `told` is read once the answer is in, after the `then` below has set it.
    let atField = false;
    void held(createAccessRole({ label: asked, permissions: [] }), () => atField).then(
      (outcome) => {
        setBusy(false);
        if (outcome.kind === "done") {
          onCreated(outcome.data);
          if (mounted.current) {
            onClose();
          }
          return;
        }
        const at = "problem" in outcome ? outcome.problem.fields : undefined;
        const own = at?.find(({ pointer }) => pointer === "/label");
        if (own === undefined || !mounted.current) {
          list?.report({ outcome, generation, names: {} });
          return;
        }
        // Said at its field, out of a notice: noted in the history of the messages.
        atField = true;
        noteRefusal(outcome, { subject: asked });
        setRefused(problemMessage(own, { locale, messages }));
        setFocused({});
      },
    );
  };

  return (
    <Dialog
      open
      onOpenChange={(opened) => {
        if (!opened) {
          onClose();
        }
      }}
    >
      <DialogContent
        aria-busy={busy}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          onClosed();
        }}
      >
        <DialogHeader>
          <DialogTitle>{t("creation")}</DialogTitle>
          <DialogDescription>{t("creationHint")}</DialogDescription>
        </DialogHeader>
        <form aria-label={t("creation")} noValidate onSubmit={submit} className="grid gap-3">
          <div className="grid gap-1">
            <Label htmlFor={field}>{columns("label")}</Label>
            <Input
              ref={input}
              id={field}
              value={label}
              required
              maxLength={LABEL_LENGTH}
              autoComplete="off"
              aria-invalid={refused === undefined ? undefined : true}
              aria-describedby={refused === undefined ? undefined : `${field}-refused`}
              onChange={(event) => {
                setLabel(event.target.value);
              }}
            />
            {refused === undefined ? null : (
              <p id={`${field}-refused`} className="text-sm text-destructive">
                {refused}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              <X aria-hidden="true" />
              {form("cancel")}
            </Button>
            <Button
              type="submit"
              aria-busy={busy || reading}
              aria-disabled={reading ? true : undefined}
            >
              <Plus aria-hidden="true" />
              {form(busy ? "sending" : "create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
