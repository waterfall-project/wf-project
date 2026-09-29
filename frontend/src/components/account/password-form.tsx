// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The change of the password of a local account (WF-ADM-0140): the current password and the new
 * one, sent as they were typed. The API judges the new one — the front copies none of its rules,
 * and a refusal is a code of the catalogue —; a session lost meanwhile leads to the sign-in page,
 * which comes back here (`OutcomeNotice`).
 */
"use client";

import { KeyRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState, useTransition } from "react";

import { changePassword } from "@/api/actions/account";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { DoneNotice } from "./done-notice";
import { textOf, WAITING } from "./form";

/** Render the form of the change of password, emptied once the API has changed it. */
export function PasswordForm() {
  const t = useTranslations("account.password");
  const id = useId();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    const form = event.currentTarget;
    const data = new FormData(form);
    const change = { current_password: textOf(data, "current"), new_password: textOf(data, "new") };
    startTransition(async () => {
      const changed = await changePassword(change);
      setOutcome(changed);
      if (changed.kind === "done") {
        form.reset();
      }
    });
  };
  return (
    <form noValidate aria-busy={pending} onSubmit={submit} className="grid max-w-sm gap-4">
      <div className="grid gap-2">
        <Label htmlFor={`${id}-current`}>{t("current")}</Label>
        <Input
          id={`${id}-current`}
          name="current"
          type="password"
          autoComplete="current-password"
          required
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${id}-new`}>{t("new")}</Label>
        <Input id={`${id}-new`} name="new" type="password" autoComplete="new-password" required />
      </div>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      <DoneNotice title={outcome?.kind === "done" ? t("changed") : undefined} />
      <div>
        <Button type="submit" aria-disabled={pending} className={WAITING}>
          <KeyRound aria-hidden="true" />
          {t("submit")}
        </Button>
      </div>
    </form>
  );
}
