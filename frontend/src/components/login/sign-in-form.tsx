// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The form of the sign-in page: the address and the password of a local account — or of an
 * account of the directory, which the API asks —, sent as they were typed. The API judges them:
 * the front checks no rule of either, and a refusal is a code of the catalogue (`OutcomeNotice`).
 *
 * Signed in, the browser loads the screen the user was headed for (`next`, which the page reads
 * through `returnTarget`), or the home page: a whole document, which reads the new session anew
 * and follows on the background tasks a lost session had interrupted (`loadDocument`).
 */
"use client";

import { LogIn } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState, useTransition } from "react";

import { signIn } from "@/api/actions/session";
import type { Outcome } from "@/api/problem";
import { textOf, WAITING } from "@/components/account/form";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useHydrated } from "@/components/use-hydrated";
import { loadDocument } from "@/navigation/document";

/** Where the browser goes once signed in: a path of this front, already checked. */
export interface SignInFormProps {
  readonly target: string;
}

/** Render the form of a local account, and sign in with it. */
export function SignInForm({ target }: SignInFormProps) {
  const t = useTranslations("signIn");
  const id = useId();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  // Disabled until React handles the sending: the browser would send the password by GET.
  const hydrated = useHydrated();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const credentials = { email: textOf(form, "email"), password: textOf(form, "password") };
    startTransition(async () => {
      const opened = await signIn(credentials);
      if (opened.kind === "done") {
        loadDocument(target);
      } else {
        setOutcome(opened);
      }
    });
  };
  return (
    <form method="post" noValidate aria-busy={pending} onSubmit={submit} className="grid gap-4">
      <div className="grid gap-2">
        <Label htmlFor={`${id}-email`}>{t("email")}</Label>
        <Input id={`${id}-email`} name="email" type="email" autoComplete="username" required />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${id}-password`}>{t("password")}</Label>
        <Input
          id={`${id}-password`}
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
      </div>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      <Button
        type="submit"
        disabled={!hydrated}
        aria-disabled={pending}
        className={`w-full ${WAITING}`}
      >
        <LogIn aria-hidden="true" />
        {t("submit")}
      </Button>
    </form>
  );
}
