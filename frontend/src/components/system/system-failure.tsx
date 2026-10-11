// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of failure: what a page shows in place of the one it could not render, never a
 * blank screen. The API out of reach is announced as such; a read the front held no session for
 * leads to the sign-in page at once, without a click, a whole document loaded — the sign-in opens
 * a session that lives, and cannot loop —; a read the API refused for want of a session offers
 * the link to it, and goes nowhere by itself: the token the front held was refused, and another
 * could be too. Either way the sign-in comes back to the screen (`loginHref`, from the address
 * the browser shows). Any other error is unexpected, with the reference that finds it again in
 * the logs when it carries one. An account Waterfall does not admit is offered the way out: the
 * realm signs it in again at each sign-in, and the shell offers it no menu of the account (#664).
 * In every case, the user may try again: the page is read anew from the server.
 *
 * A client component, as every error boundary of Next is: it receives the error as Next
 * forwards it (`failure.ts`), and the texts of the provider around it.
 */
"use client";

import { CircleAlert, LogOut, RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { SignIn, useSignInHref } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { loadDocument } from "@/navigation/document";
import { REALM_SIGN_OUT_ROUTE } from "@/navigation/login";

import { type BoundaryError, type Failure, failureOf } from "./failure";

/** The texts of each failure, in the catalogue. */
const TEXTS = {
  unreachable: "unreachable",
  session_lost: "signedOut",
  signed_out: "signedOut",
  deactivated: "deactivated",
  not_admitted: "notAdmitted",
  unexpected: "unexpected",
} as const satisfies Record<Failure["kind"], string>;

/** Lead to the sign-in page at once, the link shown until the document is loaded. */
function LeadToSignIn() {
  const href = useSignInHref();
  useEffect(() => {
    loadDocument(href);
  }, [href]);
  return <SignIn />;
}

/**
 * The way out of the session of the realm, a whole document loaded: the route sends the browser to
 * another site, which the router of Next would fetch.
 */
function RealmSignOut() {
  const t = useTranslations("failure");
  return (
    <a
      href={REALM_SIGN_OUT_ROUTE}
      className="inline-flex items-center gap-1.5 font-medium underline"
    >
      <LogOut aria-hidden="true" className="size-4" />
      {t("signOut")}
    </a>
  );
}

/** The error a boundary caught, and how to try the page again. */
export interface SystemFailureProps {
  readonly error: BoundaryError;
  readonly retry: () => void;
}

/** Render what went wrong, and the offer to try again. */
export function SystemFailure({ error, retry }: SystemFailureProps) {
  const t = useTranslations("failure");
  const failure = failureOf(error);
  const reference = failure.kind === "unexpected" ? failure.reference : undefined;
  return (
    <main className="space-y-4 px-5 py-4">
      <div role="alert" className="space-y-2">
        <h1 className="flex items-center gap-2 text-lg font-semibold">
          <CircleAlert aria-hidden="true" className="size-5 shrink-0 text-destructive" />
          {t(`${TEXTS[failure.kind]}.title`)}
        </h1>
        <p>{t(`${TEXTS[failure.kind]}.explanation`)}</p>
        {reference === undefined ? null : (
          <p className="text-muted-foreground">{t("reference", { reference })}</p>
        )}
        {failure.kind === "session_lost" ? <LeadToSignIn /> : null}
        {failure.kind === "signed_out" ? <SignIn /> : null}
        {failure.kind === "not_admitted" ? <RealmSignOut /> : null}
      </div>
      <Button type="button" size="sm" onClick={retry}>
        <RotateCcw aria-hidden="true" />
        {t("retry")}
      </Button>
    </main>
  );
}
