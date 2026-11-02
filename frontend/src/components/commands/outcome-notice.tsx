// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen says of the outcome of a server action, as the decoder of `src/api/problem.ts`
 * classed it: nothing on success; a refusal in a sentence of the catalogue, from its code and
 * parameters (WF-ARC-0110); for a stale object (412), an offer to reload it; for a conflict
 * (409), the object in conflict, named when the screen knows it — or by the label the refusal gives
 * it (`conflicting_object_label`, EP-14/L42i), a project or a sub-project the screen does not show
 * (#714) —, and the lines or the projects it names beyond the few its sentence holds, listed under
 * it in a region that scrolls (`estimate_lines`, EP-14/L53; `projects`, EP-14/L54); without a
 * session (401), the way to the sign-in page,
 * which comes back here; and, the API out of reach, that it is — the screen stays, it never goes
 * blank. The objects the refusal gives by their identifiers alone are named as the screen read them,
 * those it was given (`names`).
 *
 * Every one is an alert: it follows a command the user just gave, and is announced at once — save
 * the lines or the projects listed, which may run to thousands: out of the alert, which would read
 * them at once, named and described by its sentence (#765). A
 * screen where the work goes on after a refusal — the cells of a grid entered one after the
 * other — lets the user dismiss it (#189): told until then, whatever succeeds after it. The
 * unexpected error of the service — or of a server action that threw (`rejection.ts`) — shows its
 * reference, as the screen of failure does, for the operator to find it in the logs (WF-OBS-0020).
 */
"use client";

import { CircleAlert, LogIn, RefreshCw, WifiOff, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { useCallback, useId, useMemo } from "react";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { Button } from "@/components/ui/button";
import {
  LINES_IN_SENTENCE,
  lineName,
  namedLines,
  namedProjects,
  problemMessage,
  type ProblemText,
  projectName,
  type Say,
} from "@/i18n/problem";
import {
  type MessageDraft,
  type MessageScreen,
  noteMessage,
  useNoteMessage,
} from "@/components/notices/message-history";
import { useShownProjectLabel } from "@/components/shell/shown-project";
import { asksIdentifiers, loginHref } from "@/navigation/login";

/**
 * The names of the objects a screen shows, by identifier: what names the object of a conflict,
 * which the envelope gives by its identifier only.
 */
export type ObjectNames = Readonly<Record<string, string>>;

type Problem = components["schemas"]["Problem"];

/** No name lent: a refusal noted outside a notice is told with those it carries. */
const NO_NAMES: ObjectNames = {};

/** The offer to read anew, by a command, what its confirmation carried (412). */
export interface Reread {
  readonly label: string;
  readonly run: () => void;
}

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
  /**
   * The identifier of its sentence, for what it describes besides — the cell of a grid whose write it
   * refused —; one of its own otherwise.
   */
  readonly id?: string | undefined;
  /**
   * What the command was about, by its name, which the history of the messages notes with the
   * refusal: the object in conflict otherwise, when the refusal names one.
   */
  readonly subject?: string | undefined;
  /**
   * What a stale object (412) is read again by, in place of the reload of the screen: a command whose
   * confirmation carries what it read — the report of a merge — reads it anew, and says so.
   */
  readonly reread?: Reread | undefined;
  /**
   * What the refusal is said to, told before its sentence inside the alert — the row of a grid it was
   * refused at —, so that the alert is read whole.
   */
  readonly lead?: string | undefined;
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
 * The address of the sign-in page, which comes back to the screen shown: its path and its query;
 * with `reauthenticate`, a sign-in that asks for the identifiers again (`loginHref`).
 */
export function useSignInHref(reauthenticate = false): string {
  const query = useSearchParams().toString();
  return loginHref(`${usePathname()}${query === "" ? "" : `?${query}`}`, reauthenticate);
}

/**
 * The link to the sign-in page, which comes back to the screen shown, as the browser shows it. The
 * screen of failure offers it too, when a read wanted a session. A plain link, never one of the
 * router: `/login` sends the browser to another site, which the router would fetch, and prefetch
 * — each time starting a sign-in for nothing. For a session closed (`SESSION_REVOKED`), the sign-in
 * asks for the identifiers again (#855).
 */
export function SignIn({ reauthenticate = false }: { readonly reauthenticate?: boolean }) {
  const t = useTranslations("outcome");
  return (
    <a
      href={useSignInHref(reauthenticate)}
      className="inline-flex items-center gap-1.5 font-medium underline"
    >
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

/** The offer to read anew what a command confirmed, which has changed since it was read. */
function RereadOffer({
  reread,
  onClear,
}: {
  readonly reread: Reread;
  readonly onClear: () => void;
}) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => {
        onClear();
        reread.run();
      }}
    >
      <RefreshCw aria-hidden="true" />
      {reread.label}
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
 * The lines and the projects a refusal names beyond those its sentence holds (`LINES_IN_SENTENCE`),
 * each listed under it by its name — a line by its number and its label, a project by its label and
 * its code —, in a list that scrolls past a few, reached by the keyboard and described by the
 * sentence (`told`), out of the alert; nothing for fewer — the sentence names them.
 */
function NamedItems({ problem, told }: { readonly problem: Problem; readonly told: string }) {
  const t = useTranslations("outcome");
  const details = useTranslations("problemDetails");
  const say: Say = (key, values) => details(key, values);
  const lists = [
    { name: t("namedLines"), items: namedLines(problem.params).map((line) => lineName(line, say)) },
    {
      name: t("namedProjects"),
      items: namedProjects(problem.params).map((project) => projectName(project, say)),
    },
  ].filter(({ items }) => items.length > LINES_IN_SENTENCE);
  return lists.map(({ name, items }) => (
    <ul
      key={name}
      aria-label={name}
      aria-describedby={told}
      tabIndex={0}
      className="max-h-40 list-disc space-y-0.5 overflow-y-auto rounded-md pl-6 outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {items.map((item, index) => (
        // Two structures may number a line alike: the key takes its rank too.
        <li key={`${index.toString()}:${item}`}>{item}</li>
      ))}
    </ul>
  ));
}

/**
 * The identifier of the paragraph that names the object in conflict, from that of the sentence of
 * the notice: what a cell refused is described by besides (EP-14/L44d).
 */
export function conflictId(told: string): string {
  return `${told}-object`;
}

/**
 * What describes what an outcome refused, from the identifier of the sentence of its notice: the
 * sentence, and the paragraph that names the object in conflict when the refusal names one.
 */
export function refusalDescription(outcome: Outcome<unknown> | undefined, told: string): string {
  return outcome !== undefined &&
    "conflictingObjectId" in outcome &&
    outcome.conflictingObjectId !== null
    ? `${told} ${conflictId(told)}`
    : told;
}

/** The identifier of the sentence of a notice: the one given, or one of its own. */
function useSentenceId(id: string | undefined): string {
  const own = useId();
  return id ?? own;
}

/** The correlation identifier an unexpected error shows (WF-OBS-0020); none for another refusal. */
function referenceOf(problem: Problem): string | undefined {
  return problem.code === "INTERNAL_ERROR" ? problem.correlation_id : undefined;
}

/** A refusal, as a notice tells it. */
interface Told {
  readonly refusal: Exclude<Outcome<unknown>, { kind: "done" }>;
  /** Its sentence, from the catalogue. */
  readonly sentence: string;
  /** The name of the object in conflict, when it names one. */
  readonly name: string | undefined;
}

/**
 * What a notice tells of a refusal, in a sentence of the catalogue, and the object it names, by its
 * name; nothing on success, nor before any outcome.
 */
function told(
  outcome: Outcome<unknown> | undefined,
  known: ObjectNames,
  say: { readonly unreachable: string; readonly problem: (problem: Problem) => string },
): Told | undefined {
  if (outcome === undefined || outcome.kind === "done") {
    return undefined;
  }
  if (outcome.kind === "unreachable") {
    return { refusal: outcome, sentence: say.unreachable, name: undefined };
  }
  const { problem, conflictingObjectId } = outcome;
  return {
    refusal: outcome,
    sentence: say.problem(problem),
    name:
      conflictingObjectId === null
        ? undefined
        : (known[conflictingObjectId] ?? labelOf(problem, conflictingObjectId)),
  };
}

/**
 * What the history of the messages notes of a refusal told: about the object given, else the one in
 * conflict.
 */
function draftOf(
  refusal: Told,
  subject: string | undefined,
  screen?: MessageScreen,
  detail?: string,
): MessageDraft {
  return {
    tone: "refusal",
    sentence: refusal.sentence,
    detail,
    object: subject ?? refusal.name,
    reference: "problem" in refusal.refusal ? referenceOf(refusal.refusal.problem) : undefined,
    screen,
  };
}

/** How a refusal is told, in the language of the moment, with the names the screen lends. */
function useSay(known: ObjectNames) {
  const t = useTranslations("outcome");
  const locale = useLocale();
  const messages = useMessages();
  return useMemo(
    () => ({
      unreachable: t("unreachable"),
      problem: (problem: ProblemText) =>
        problemMessage(problem, { locale, messages, names: known }),
    }),
    [t, locale, messages, known],
  );
}

/**
 * The refusal a notice tells, noted in the history of the messages (`message-history.ts`) once
 * told — with the object it is about, the one the screen gives, else the object in conflict.
 */
function useTold(
  outcome: Outcome<unknown> | undefined,
  known: ObjectNames,
  subject: string | undefined,
): Told | undefined {
  const refusal = told(outcome, known, useSay(known));
  useNoteMessage(
    refusal?.refusal,
    refusal === undefined ? undefined : draftOf(refusal, subject),
    useShownProjectLabel(),
  );
  return refusal;
}

/** What a refusal noted without a notice is about, where it was made, and what tells the rest. */
export interface NotedRefusal {
  /** What the command was about, by its name; the object in conflict otherwise. */
  readonly subject?: string | undefined;
  /** The screen it was made on, when it is not the one shown: a screen left since. */
  readonly screen?: MessageScreen | undefined;
  /** The parts of it a notice tells besides (`noteMessage`), which note nothing more. */
  readonly parts?: readonly (object | undefined)[] | undefined;
}

/**
 * Note in the history of the messages a refusal the screen tells otherwise than by a notice — at the
 * fields of a form, by the bar of the shell —, in the sentence a notice would tell it in, once, what
 * its fields refuse in a second sentence, each reason once: the same outcome told by a notice after
 * it notes nothing more. Nothing for an outcome done.
 */
export function useNoteRefusal(): (outcome: Outcome<unknown>, noted?: NotedRefusal) => void {
  const say = useSay(NO_NAMES);
  const project = useShownProjectLabel();
  return useCallback(
    (outcome: Outcome<unknown>, { subject, screen, parts }: NotedRefusal = {}) => {
      const refusal = told(outcome, NO_NAMES, say);
      if (refusal === undefined) {
        return;
      }
      const fields = "problem" in outcome ? (outcome.problem.fields ?? []) : [];
      // Each sentence once: two fields refused for the same reason say it once (#1181).
      const sentences = [...new Set(fields.map((field) => say.problem(field)))];
      const detail = sentences.length === 0 ? undefined : sentences.join(" ");
      noteMessage(outcome, draftOf(refusal, subject, screen, detail), project(), parts);
    },
    [say, project],
  );
}

/**
 * Tell of the outcome of an action; nothing on success. A refusal told is noted in the history of the
 * messages, and announced by this notice alone: the history says nothing aloud.
 */
export function OutcomeNotice({
  outcome,
  names = {},
  onClear,
  dismissible = false,
  onDismissed,
  id,
  subject,
  reread,
  lead,
}: OutcomeNoticeProps) {
  const t = useTranslations("outcome");
  const failure = useTranslations("failure");
  const sentenceId = useSentenceId(id);
  const told = useTold(outcome, names, subject);
  if (told === undefined) {
    return null;
  }
  const { refusal } = told;
  const dismissed = () => {
    onClear();
    onDismissed?.();
  };
  const dismiss = dismissible ? <Dismiss onClear={dismissed} told={sentenceId} /> : null;
  const leading = lead === undefined ? null : <p className="font-medium">{lead}</p>;
  if (refusal.kind === "unreachable") {
    return (
      <div role="alert" className={ALERT}>
        {leading}
        <p id={sentenceId} className={SENTENCE}>
          <WifiOff aria-hidden="true" className={ICON} />
          {told.sentence}
        </p>
        {dismiss}
      </div>
    );
  }
  const { kind, problem } = refusal;
  const { name } = told;
  // The unexpected error shows its reference, as the screen of failure does (WF-OBS-0020): the
  // correlation identifier of the API, or the reference of a server action that threw (`rejected`).
  const reference = referenceOf(problem);
  return (
    <div className={ALERT}>
      <div role="alert" className="space-y-1">
        {leading}
        <p id={sentenceId} className={SENTENCE}>
          <CircleAlert aria-hidden="true" className={ICON} />
          {told.sentence}
        </p>
        {reference === undefined ? null : <p>{failure("reference", { reference })}</p>}
        {name === undefined ? null : (
          <p id={conflictId(sentenceId)}>{t("conflictingObject", { name })}</p>
        )}
        {kind === "signed_out" ? <SignIn reauthenticate={asksIdentifiers(problem.code)} /> : null}
        {/* Reloading forgets the outcome as dismissing it does, the focus given back the same way. */}
        {kind === "stale" ? (
          reread === undefined ? (
            <Reload onClear={dismissed} />
          ) : (
            <RereadOffer reread={reread} onClear={dismissed} />
          )
        ) : null}
        {dismiss}
      </div>
      <NamedItems problem={problem} told={sentenceId} />
    </div>
  );
}
