// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen says of the outcome of a server action, as the decoder of `src/api/problem.ts`
 * classed it: nothing on success; a refusal in a sentence of the catalogue, from its code and
 * parameters (WF-ARC-0110); for a stale object (412), an offer to reload it; for a conflict
 * (409), the object in conflict, named when the screen knows it — or by the label the refusal gives
 * it (`conflicting_object_label`, EP-14/L42i), a project or a sub-project the screen does not show
 * (#714) —, and the lines it names beyond the few its sentence holds, listed under it in a region
 * that scrolls (`estimate_lines`, EP-14/L53); without a session (401), the way to the sign-in page,
 * which comes back here; and, the API out of reach, that it is — the screen stays, it never goes
 * blank.
 *
 * Every one is an alert: it follows a command the user just gave, and is announced at once. A
 * screen where the work goes on after a refusal — the cells of a grid entered one after the
 * other — lets the user dismiss it (#189): told until then, whatever succeeds after it. The
 * unexpected error of the service — or of a server action that threw (`rejection.ts`) — shows its
 * reference, as the screen of failure does, for the operator to find it in the logs (WF-OBS-0020).
 */
"use client";

import { CircleAlert, LogIn, RefreshCw, WifiOff, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { useId } from "react";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { Button } from "@/components/ui/button";
import { LINES_IN_SENTENCE, lineName, namedLines, problemMessage } from "@/i18n/problem";
import { loginHref } from "@/navigation/login";

/**
 * The names of the objects a screen shows, by identifier: what names the object of a conflict,
 * which the envelope gives by its identifier only.
 */
export type ObjectNames = Readonly<Record<string, string>>;

type Problem = components["schemas"]["Problem"];

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

/**
 * The label a refusal gives the object it is about (`conflicting_object_label`), from the part of
 * the envelope that names it — itself, or a refusal by field —; none when it gives none.
 */
function labelOf({ params, fields }: Problem, id: string): string | undefined {
  const label = [params, ...(fields ?? []).map((field) => field.params)].find(
    (each) => each?.conflicting_object_id === id,
  )?.conflicting_object_label;
  return typeof label === "string" && label !== "" ? label : undefined;
}

const ALERT = "space-y-1 text-sm text-destructive";
const SENTENCE = "flex items-start gap-1.5";
const ICON = "mt-0.5 size-4 shrink-0";

/**
 * The link to the sign-in page, which comes back to the screen shown: its path and its query,
 * as the browser shows them. The screen of failure offers it too, when a read wanted a session.
 */
export function SignIn() {
  const t = useTranslations("outcome");
  const query = useSearchParams().toString();
  const screen = `${usePathname()}${query === "" ? "" : `?${query}`}`;
  return (
    <Link
      href={loginHref(screen)}
      className="inline-flex items-center gap-1.5 font-medium underline"
    >
      <LogIn aria-hidden="true" className="size-4" />
      {t("signIn")}
    </Link>
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

/**
 * The lines a refusal names beyond those its sentence holds (`LINES_IN_SENTENCE`), listed under it,
 * each by its number and its label, in a list that scrolls past a few, reached by the keyboard;
 * nothing for fewer — the sentence names them.
 */
function NamedLines({ problem }: { readonly problem: Problem }) {
  const t = useTranslations("outcome");
  const details = useTranslations("problemDetails");
  const lines = namedLines(problem.params);
  if (lines.length <= LINES_IN_SENTENCE) {
    return null;
  }
  return (
    <ul
      aria-label={t("namedLines")}
      tabIndex={0}
      className="max-h-40 list-disc space-y-0.5 overflow-y-auto rounded-md pl-6 outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {lines.map((line, index) => (
        // Two structures may number a line alike: the key takes its rank too.
        <li key={`${line.row_number.toString()}:${index.toString()}`}>
          {lineName(line, (key, values) => details(key, values))}
        </li>
      ))}
    </ul>
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
  const name =
    conflictingObjectId === null
      ? undefined
      : (names[conflictingObjectId] ?? labelOf(problem, conflictingObjectId));
  // The unexpected error shows its reference, as the screen of failure does (WF-OBS-0020): the
  // correlation identifier of the API, or the reference of a server action that threw (`rejected`).
  const reference = problem.code === "INTERNAL_ERROR" ? problem.correlation_id : undefined;
  return (
    <div role="alert" className={ALERT}>
      <p id={told} className={SENTENCE}>
        <CircleAlert aria-hidden="true" className={ICON} />
        {problemMessage(problem, { locale, messages })}
      </p>
      <NamedLines problem={problem} />
      {reference === undefined ? null : <p>{failure("reference", { reference })}</p>}
      {name === undefined ? null : <p>{t("conflictingObject", { name })}</p>}
      {kind === "signed_out" ? <SignIn /> : null}
      {/* Reloading forgets the outcome as dismissing it does, the focus given back the same way. */}
      {kind === "stale" ? <Reload onClear={dismissed} /> : null}
      {dismiss}
    </div>
  );
}
