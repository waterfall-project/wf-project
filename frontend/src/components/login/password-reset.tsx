// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The password forgotten, in two steps (WF-ADM-0140): the address of the account, to which the
 * API sends a link — without saying whether an account has it, and neither does the screen —;
 * then, from the link, the new password, with the token the link carries. The API judges the
 * password: the front checks none of its rules, and a refusal is a code of the catalogue — a
 * link expired or used already among them, which the screen offers to ask for again.
 */
"use client";

import { LogIn, RotateCcw, Save, Send } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { askPasswordReset, resetPassword } from "@/api/actions/session";
import type { Outcome } from "@/api/problem";
import { DoneNotice } from "@/components/notices/done-notice";
import { textOf, WAITING } from "@/components/account/form";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LOGIN_ROUTE, PASSWORD_RESET_ROUTE } from "@/navigation/login";

const LINK = "inline-flex items-center gap-1.5 font-medium underline";

/** The outcome of the last request of a form, and how to send one. */
function useRequest() {
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  // A request under way: a second one waits for its outcome, the button keeping the focus.
  const send = (request: () => Promise<Outcome<unknown>>) => {
    if (pending) {
      return;
    }
    startTransition(async () => {
      setOutcome(await request());
    });
  };
  const clear = () => {
    setOutcome(undefined);
  };
  return { outcome, pending, send, clear };
}

/** The first step: the address of the account, to which the API sends a link. */
export function AskResetLink() {
  const t = useTranslations("passwordReset");
  const id = useId();
  const { outcome, pending, send, clear } = useRequest();
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    const email = textOf(new FormData(event.currentTarget), "email");
    send(() => askPasswordReset(email));
  };
  return (
    <form noValidate aria-busy={pending} onSubmit={submit} className="grid gap-4">
      <div className="grid gap-2">
        <Label htmlFor={`${id}-email`}>{t("email")}</Label>
        <Input id={`${id}-email`} name="email" type="email" autoComplete="username" required />
      </div>
      <OutcomeNotice outcome={outcome} onClear={clear} />
      <DoneNotice title={outcome?.kind === "done" ? t("sent") : undefined} />
      <Button type="submit" aria-disabled={pending} className={`w-full ${WAITING}`}>
        <Send aria-hidden="true" />
        {t("send")}
      </Button>
    </form>
  );
}

/** The token the link of the reset carries. */
export interface ChoosePasswordProps {
  readonly token: string;
}

/** The second step: the new password, set with the token of the link. */
export function ChoosePassword({ token }: ChoosePasswordProps) {
  const t = useTranslations("passwordReset");
  const id = useId();
  const { outcome, pending, send, clear } = useRequest();
  const saved = outcome?.kind === "done";
  const signIn = useRef<HTMLAnchorElement>(null);
  // The button goes once the password is saved: the focus goes to the way on, the sign-in page.
  useEffect(() => {
    if (saved) {
      signIn.current?.focus();
    }
  }, [saved]);
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    const password = textOf(new FormData(event.currentTarget), "password");
    send(() => resetPassword(token, password));
  };
  return (
    <form noValidate aria-busy={pending} onSubmit={submit} className="grid gap-4">
      <div className="grid gap-2">
        <Label htmlFor={`${id}-password`}>{t("newPassword")}</Label>
        <Input
          id={`${id}-password`}
          name="password"
          type="password"
          autoComplete="new-password"
          required
          disabled={saved}
        />
      </div>
      <OutcomeNotice outcome={outcome} onClear={clear} />
      {outcome?.kind === "conflict" ? (
        <Link href={PASSWORD_RESET_ROUTE} className={`${LINK} text-sm`}>
          <RotateCcw aria-hidden="true" className="size-4" />
          {t("askAgain")}
        </Link>
      ) : null}
      <DoneNotice title={saved ? t("saved") : undefined}>
        {saved ? (
          <Link ref={signIn} href={LOGIN_ROUTE} className={LINK}>
            <LogIn aria-hidden="true" className="size-4" />
            {t("signIn")}
          </Link>
        ) : undefined}
      </DoneNotice>
      {saved ? null : (
        <Button type="submit" aria-disabled={pending} className={`w-full ${WAITING}`}>
          <Save aria-hidden="true" />
          {t("save")}
        </Button>
      )}
    </form>
  );
}
