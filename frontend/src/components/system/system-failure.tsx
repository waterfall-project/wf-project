// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of failure: what a page shows in place of the one it could not render, never a
 * blank screen. The API out of reach is announced as such; any other error as unexpected,
 * with the reference that finds it again in the logs when it carries one. Either way, the
 * user may try again: the page is read anew from the server.
 *
 * A client component, as every error boundary of Next is: it receives the error as Next
 * forwards it (`failure.ts`), and the texts of the provider around it.
 */
"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

import { type BoundaryError, failureOf } from "./failure";

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
    <main className="space-y-4 p-6">
      <div role="alert" className="space-y-2">
        <h1 className="text-2xl font-semibold">{t(`${failure.kind}.title`)}</h1>
        <p>{t(`${failure.kind}.explanation`)}</p>
        {reference === undefined ? null : (
          <p className="text-muted-foreground">{t("reference", { reference })}</p>
        )}
      </div>
      <Button type="button" onClick={retry}>
        {t("retry")}
      </Button>
    </main>
  );
}
