// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen says of the outcome of a server action, as the decoder of `src/api/problem.ts`
 * classed it: nothing on success; a refusal in a sentence of the catalogue, from its code and
 * parameters (WF-ARC-0110); for a stale object (412), an offer to reload it; for a conflict
 * (409), the object in conflict, named when the screen knows it; without a session (401), the
 * way to the sign-in page, which comes back here; and, the API out of reach, that it is — the
 * screen stays, it never goes blank.
 *
 * Every one is an alert: it follows a command the user just gave, and is announced at once. A
 * screen where the work goes on after a refusal — the cells of a grid entered one after the
 * other — lets the user dismiss it (#189): told until then, whatever succeeds after it. The
 * unexpected error of the service — or of a server action that threw (`rejection.ts`) — shows its
 * reference, as the screen of failure does, for the operator to find it in the logs (WF-OBS-0020).
 */
"use client";

import { CircleAlert, LogIn, RefreshCw, WifiOff, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { useId } from "react";

import type { Outcome } from "@/api/problem";
import { Button } from "@/components/ui/button";
import { problemMessage } from "@/i18n/problem";
import { loginHref } from "@/navigation/login";

/**
 * The names of the objects a screen shows, by identifier: what names the object of a conflict,
 * which the envelope gives by its identifier only.
 */
export type ObjectNames = Readonly<Record<string, string>>;

/** The outcome to tell of, and what the screen knows to tell it with. */
export interface OutcomeNoticeProps {
  /** The outcome of the last action; nothing to tell before any. */
  readonly outcome: Outcome<unknown> | undefined;
  readonly names?: ObjectNames | undefined;
  /** Forget the outcome: the screen reloads what it shows, and the notice has done its part. */
  readonly onClear: () => void;
  /** Whether the notice offers to dismiss it, forgetting the outcome. */
  readonly dismissible?: boolean | undefined;
  /**
   * Once dismissed — or the screen reloaded from a stale object —: where the screen gives the focus
   * back, which the notice took away with its button — never left to fall to the page.
   */
  readonly onDismissed?: (() => void) | undefined;
}

const ALERT = "space-y-1 text-sm text-destructive";
const SENTENCE = "flex items-start gap-1.5";
const ICON = "mt-0.5 size-4 shrink-0";

/** The address of the sign-in page, which comes back to the screen shown: its path and its query. */
export function useSignInHref(): string {
  const query = useSearchParams().toString();
  return loginHref(`${usePathname()}${query === "" ? "" : `?${query}`}`);
}

/**
 * The link to the sign-in page, which comes back to the screen shown, as the browser shows it. The
 * screen of failure offers it too, when a read wanted a session. A plain link, never one of the
 * router: `/login` sends the browser to another site, which the router would fetch, and prefetch
 * — each time starting a sign-in for nothing.
 */
export function SignIn() {
  const t = useTranslations("outcome");
  return (
    <a href={useSignInHref()} className="inline-flex items-center gap-1.5 font-medium underline">
      <LogIn aria-hidden="true" className="size-4" />
      {t("signIn")}
    </a>
  );
}

/** The offer to reload what the screen shows, read anew by the server. */
function Reload({ onClear }: { readonly onClear: () => void }) {
  const t = useTranslations("outcome");
  const router = useRouter();
  const reload = () => {
    onClear();
    router.refresh();
  };
  return (
    <Button type="button" variant="outline" size="sm" onClick={reload}>
      <RefreshCw aria-hidden="true" />
      {t("reload")}
    </Button>
  );
}

/**
 * The offer to dismiss a notice, which forgets the outcome it tells — described by the sentence of its
 * notice, so that among several a reader hears which one it dismisses.
 */
function Dismiss({ onClear, told }: { readonly onClear: () => void; readonly told: string }) {
  const t = useTranslations("outcome");
  return (
    <Button type="button" variant="outline" size="sm" aria-describedby={told} onClick={onClear}>
      <X aria-hidden="true" />
      {t("dismiss")}
    </Button>
  );
}

/** Tell of the outcome of an action; nothing on success. */
export function OutcomeNotice({
  outcome,
  names = {},
  onClear,
  dismissible = false,
  onDismissed,
}: OutcomeNoticeProps) {
  const t = useTranslations("outcome");
  const failure = useTranslations("failure");
  const locale = useLocale();
  const messages = useMessages();
  const told = useId();
  if (outcome === undefined || outcome.kind === "done") {
    return null;
  }
  const dismissed = () => {
    onClear();
    onDismissed?.();
  };
  const dismiss = dismissible ? <Dismiss onClear={dismissed} told={told} /> : null;
  if (outcome.kind === "unreachable") {
    return (
      <div role="alert" className={ALERT}>
        <p id={told} className={SENTENCE}>
          <WifiOff aria-hidden="true" className={ICON} />
          {t("unreachable")}
        </p>
        {dismiss}
      </div>
    );
  }
  const { kind, problem, conflictingObjectId } = outcome;
  const name = conflictingObjectId === null ? undefined : names[conflictingObjectId];
  // The unexpected error shows its reference, as the screen of failure does (WF-OBS-0020): the
  // correlation identifier of the API, or the reference of a server action that threw (`rejected`).
  const reference = problem.code === "INTERNAL_ERROR" ? problem.correlation_id : undefined;
  return (
    <div role="alert" className={ALERT}>
      <p id={told} className={SENTENCE}>
        <CircleAlert aria-hidden="true" className={ICON} />
        {problemMessage(problem, { locale, messages })}
      </p>
      {reference === undefined ? null : <p>{failure("reference", { reference })}</p>}
      {name === undefined ? null : <p>{t("conflictingObject", { name })}</p>}
      {kind === "signed_out" ? <SignIn /> : null}
      {/* Reloading forgets the outcome as dismissing it does, the focus given back the same way. */}
      {kind === "stale" ? <Reload onClear={dismissed} /> : null}
      {dismiss}
    </div>
  );
}
