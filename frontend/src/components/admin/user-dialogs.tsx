// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dialogs of the table of the accounts (US-0360): the creation of a local account, and the link
 * by which the holder of a local account sets its password, given once (WF-ADM-0140).
 *
 * The creation asks the last name, the first name and the address — what the contract requires
 * (`UserCreate`): its roles are attributed in the table afterwards, its node is EP-05's. A field left
 * blank is refused at the field before anything is asked, as the server would (WF-ADM-0050), the first
 * one refused taking the focus; the rest is the server's to judge: a refusal by field (422, or 409
 * `ALREADY_EXISTS` on the address already held) at each field it points at, by the catalogue of the
 * codes of error; any other, under the form, which stays open to be corrected. The dialog may be
 * closed meanwhile: a creation answered is said all the same, and a refusal told above the table, on
 * the reading the form was sent from (`useListReport`).
 *
 * The link is shown whole, read-only, to be copied and handed over by another channel, with the instant
 * it ceases to be valid, in the local time of the workstation: it is never read again. No screen
 * shows, asks or takes a password (WF-ADM-0140).
 */
"use client";

import { Copy, Plus, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { createUser } from "@/api/actions/users";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { LocalTime } from "@/components/local-time";
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

import type { User } from "./admin-grids";
import { EMAIL_LENGTH, NAME_LENGTH } from "./user-address";

type FieldProblem = components["schemas"]["FieldProblem"];

/** The fields of the creation, in their order, by the name the contract gives each. */
const FIELDS = [
  ["last_name", "lastName", NAME_LENGTH],
  ["first_name", "firstName", NAME_LENGTH],
  ["email", "email", EMAIL_LENGTH],
] as const;

type Field = (typeof FIELDS)[number][0];

/** What the form holds, by field. */
type Draft = Readonly<Record<Field, string>>;

const EMPTY: Draft = { last_name: "", first_name: "", email: "" };

/**
 * The refusals of the server the form says at a field, and the outcome to tell under it: none when
 * every refusal is said at its field.
 */
function placed(outcome: Outcome<unknown>): {
  readonly refused: ReadonlyMap<Field, FieldProblem>;
  readonly told: Outcome<unknown> | undefined;
} {
  const refused = new Map<Field, FieldProblem>();
  if (!("problem" in outcome) || outcome.problem.fields === undefined) {
    return { refused, told: outcome };
  }
  const rest = outcome.problem.fields.filter((problem) => {
    const field = FIELDS.find(([name]) => problem.pointer === `/${name}`)?.[0];
    if (field !== undefined) {
      refused.set(field, problem);
    }
    return field === undefined;
  });
  if (refused.size === 0) {
    return { refused, told: outcome };
  }
  return {
    refused,
    told:
      rest.length === 0 ? undefined : { ...outcome, problem: { ...outcome.problem, fields: rest } },
  };
}

/** Render the dialog that creates a local account. */
export function UserCreation({
  onCreated,
  onClose,
  onClosed,
}: {
  /** Take the account created, the dialog open or closed. */
  readonly onCreated: (user: User) => void;
  readonly onClose: () => void;
  /** Give the focus back where the dialog was opened from, once it has closed. */
  readonly onClosed: () => void;
}) {
  const t = useTranslations("admin.users");
  const form = useTranslations("reference.form");
  const columns = useTranslations("grid.columns");
  const locale = useLocale();
  const messages = useMessages();
  const list = useListReport();
  const id = useId();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [problems, setProblems] = useState<ReadonlyMap<Field, FieldProblem>>(() => new Map());
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const controls = useRef<Partial<Record<Field, HTMLInputElement | null>>>({});
  const open = useRef(true);
  useEffect(() => {
    open.current = true;
    return () => {
      open.current = false;
    };
  }, []);

  /** Say the refusals at their fields, and give the focus to the first one refused. */
  const refuse = (refused: ReadonlyMap<Field, FieldProblem>) => {
    setProblems(refused);
    const first = FIELDS.find(([name]) => refused.has(name))?.[0];
    if (first !== undefined) {
      controls.current[first]?.focus();
    }
  };

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    setOutcome(undefined);
    // A name or an address takes a character that is not blank (WF-ADM-0050).
    const values = {
      last_name: draft.last_name.trim(),
      first_name: draft.first_name.trim(),
      email: draft.email.trim(),
    };
    const blank = new Map<Field, FieldProblem>(
      FIELDS.filter(([name]) => values[name] === "").map(([name]) => [
        name,
        { pointer: `/${name}`, code: "VALUE_REQUIRED" },
      ]),
    );
    refuse(blank);
    if (blank.size > 0) {
      return;
    }
    // The reading the form is sent from: a refusal answered once the dialog is gone is told on it.
    const reading = list?.reading ?? "";
    startTransition(async () => {
      const answer = await createUser(values).catch(rejected);
      if (answer.kind === "done") {
        onCreated(answer.data);
        onClose();
      } else if (!open.current) {
        list?.report({ outcome: answer, reading, names: {} });
      } else {
        const told = placed(answer);
        refuse(told.refused);
        setOutcome(told.told);
      }
    });
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
        aria-busy={pending}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          onClosed();
        }}
      >
        <DialogHeader>
          <DialogTitle>{t("create")}</DialogTitle>
          <DialogDescription>{t("creationHint")}</DialogDescription>
        </DialogHeader>
        <form aria-label={t("create")} noValidate onSubmit={submit} className="grid gap-3">
          {FIELDS.map(([name, label, length]) => {
            const problem = problems.get(name);
            const own = `${id}-${name}`;
            return (
              <div key={name} className="grid gap-1">
                <Label htmlFor={own}>{columns(label)}</Label>
                <Input
                  ref={(element) => {
                    controls.current[name] = element;
                  }}
                  id={own}
                  type={name === "email" ? "email" : "text"}
                  autoComplete="off"
                  value={draft[name]}
                  maxLength={length}
                  aria-required
                  aria-invalid={problem === undefined ? undefined : true}
                  aria-describedby={problem === undefined ? undefined : `${own}-problem`}
                  onChange={(changed) => {
                    setDraft({ ...draft, [name]: changed.target.value });
                  }}
                />
                {problem === undefined ? null : (
                  <p id={`${own}-problem`} className="text-sm text-destructive">
                    {problemMessage(problem, { locale, messages })}
                  </p>
                )}
              </div>
            );
          })}
          <OutcomeNotice
            outcome={outcome}
            onClear={() => {
              setOutcome(undefined);
            }}
            onDismissed={onClose}
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              <X aria-hidden="true" />
              {form("cancel")}
            </Button>
            <Button type="submit" aria-busy={pending}>
              <Plus aria-hidden="true" />
              {form(pending ? "sending" : "create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Render the link given for an account, to be copied: the whole link, read-only and selected, and the
 * instant it ceases to be valid; a copy said once done, or the link selected to be copied by hand when
 * the browser refuses it.
 */
export function SetupLinkDialog({
  link,
  name,
  onClose,
  onClosed,
}: {
  readonly link: components["schemas"]["PasswordSetupLink"];
  /** The name of the account, as the table shows it. */
  readonly name: string;
  readonly onClose: () => void;
  readonly onClosed: () => void;
}) {
  const t = useTranslations("admin.users");
  const field = useId();
  const input = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState<boolean>();
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
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          input.current?.select();
          input.current?.focus();
        }}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          onClosed();
        }}
      >
        <DialogHeader>
          <DialogTitle>{t("linkTitle", { name })}</DialogTitle>
          <DialogDescription>{t("linkHint")}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-1">
          <Label htmlFor={field}>{t("link")}</Label>
          <Input
            ref={input}
            id={field}
            readOnly
            value={link.url}
            aria-describedby={`${field}-expiry`}
            onFocus={(event) => {
              event.currentTarget.select();
            }}
          />
          <p id={`${field}-expiry`} className="text-xs text-muted-foreground">
            {t.rich("linkExpiry", { expiry: () => <LocalTime value={link.expires_at} /> })}
          </p>
        </div>
        <p role="status" className="min-h-5 text-sm text-muted-foreground">
          {copied === undefined ? null : t(copied ? "linkCopied" : "linkSelected")}
        </p>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              // The clipboard is absent outside a secure context: the link is then selected.
              void Promise.resolve()
                .then(() => navigator.clipboard.writeText(link.url))
                .then(
                  () => {
                    setCopied(true);
                  },
                  () => {
                    setCopied(false);
                    input.current?.select();
                    input.current?.focus();
                  },
                );
            }}
          >
            <Copy aria-hidden="true" />
            {t("copyLink")}
          </Button>
          <Button type="button" onClick={onClose}>
            <X aria-hidden="true" />
            {t("closeLink")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
