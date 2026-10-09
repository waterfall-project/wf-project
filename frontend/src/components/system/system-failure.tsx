// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of failure: what a page shows in place of the one it could not render, never a
 * blank screen. The API out of reach is announced as such; a read the API refused for want of
 * a session leads to the sign-in page, which comes back to the screen (`loginHref`, from the
 * address the browser shows); any other error is unexpected, with the reference that finds it
 * again in the logs when it carries one. Either way, the user may try again: the page is read
 * anew from the server.
 *
 * A client component, as every error boundary of Next is: it receives the error as Next
 * forwards it (`failure.ts`), and the texts of the provider around it.
 */
"use client";

import { CircleAlert, RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";

import { SignIn } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";

import { type BoundaryError, type Failure, failureOf } from "./failure";

/** The texts of each failure, in the catalogue. */
const TEXTS = {
  unreachable: "unreachable",
  signed_out: "signedOut",
  deactivated: "deactivated",
  unexpected: "unexpected",
} as const satisfies Record<Failure["kind"], string>;

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
        {failure.kind === "signed_out" ? <SignIn /> : null}
      </div>
      <Button type="button" size="sm" onClick={retry}>
        <RotateCcw aria-hidden="true" />
        {t("retry")}
      </Button>
    </main>
  );
}
