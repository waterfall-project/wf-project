// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The history of the messages of the session (#1043): every outcome of a command the screens told
 * — a refusal as `OutcomeNotice` or a notice of a grid said it, a success a confirmation said, a
 * background task handed over or ended —, kept so that a notice closed, or left behind on another
 * screen, can be read again. It is an aid to the user, for themselves alone: not the audit log
 * (WF-SEC-0030), which proves what was done and lives on the server.
 *
 * Each message keeps when it was told, the screen it was told on — its address, which a link
 * leads back to, and the project the screen showed —, the object it was about when the notice
 * names one, the sentence of the notice, drawn from the same catalogue, and, for the unexpected
 * error, its correlation identifier, for the operator to follow it in the logs (WF-OBS-0020). The
 * sentence is kept as it was told, in the language of the moment: the history repeats what was
 * said, never a sentence written again.
 *
 * The history is the session's, in the browser: kept in the storage of the tab (`sessionStorage`)
 * across a reload, the last `MESSAGES_KEPT`, and forgotten on signing out — the next user of the tab
 * reads none of it. Nothing is asked of the API. A store outside React (défaut n° 18): only the
 * button of the panel and the panel subscribe to it; a notice writes to it once it has told its
 * outcome — once per outcome, however often it renders it, and however many notices tell it —,
 * without announcing anything: the notice is the alert, the history repeats nothing aloud.
 *
 * A refusal the panel has not shown yet is unread: the button of the panel counts them.
 */
"use client";

import { useEffect } from "react";

import { isApplicationPath } from "@/navigation/application-path";

/** The key of the storage of the tab under which the messages are kept. */
export const MESSAGES_KEY = "wf_messages";

/** How many messages the history keeps: the last ones. */
export const MESSAGES_KEPT = 100;

/** Whether a message tells a success, or a refusal — the API out of reach and a task failed too. */
export type MessageTone = "success" | "refusal";

/** The screen a message was told on: its address, and the project it showed, by its label. */
export interface MessageScreen {
  readonly href: string;
  readonly project?: string | undefined;
}

/** A message of the history. */
export interface Message {
  /** Its rank in the session, from 1: the later, the greater. */
  readonly id: number;
  /** When it was told, an instant of the workstation. */
  readonly at: string;
  readonly tone: MessageTone;
  /** The sentence of the notice, as it was told. */
  readonly sentence: string;
  /** The sentence that follows it, when the notice says two: the motive of a task failed. */
  readonly detail?: string | undefined;
  /** What the outcome was about, when the notice names it: an object in conflict, a task. */
  readonly object?: string | undefined;
  /** The correlation identifier of an unexpected error. */
  readonly reference?: string | undefined;
  readonly screen: MessageScreen;
}

/** What a notice tells the history: the rest is the history's to note. */
export interface MessageDraft {
  readonly tone: MessageTone;
  readonly sentence: string;
  readonly detail?: string | undefined;
  readonly object?: string | undefined;
  readonly reference?: string | undefined;
  /** The screen, when it is not the one shown: a task ends on another screen than its own. */
  readonly screen?: MessageScreen | undefined;
}

/** The messages of the session, and the last one the panel showed. */
export interface MessageHistory {
  readonly messages: readonly Message[];
  /** The rank of the last message shown: a refusal after it is unread. */
  readonly seen: number;
}

/** No message: the server's, and the browser's once signed out. */
export const NO_MESSAGES: MessageHistory = { messages: [], seen: 0 };

/** The history, read from the storage of the tab at its first reading. */
let history: MessageHistory | undefined;
/** The outcomes already noted, by identity: a notice rendered again notes nothing more. */
let noted = new WeakSet<object>();
/** Those the history is told to when it changes. */
const listeners = new Set<() => void>();

/**
 * Whether a value read back is a screen kept here: an address of the application
 * (`isApplicationPath`, the guard of the way back from the sign-in).
 */
export function isScreen(value: unknown): value is MessageScreen {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const screen = value as Partial<Record<keyof MessageScreen, unknown>>;
  return (
    typeof screen.href === "string" &&
    isApplicationPath(screen.href) &&
    (screen.project === undefined || typeof screen.project === "string")
  );
}

/** Whether a value read back is a message kept here. */
function isMessage(value: unknown): value is Message {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const message = value as Partial<Record<keyof Message, unknown>>;
  const optional = (field: unknown) => field === undefined || typeof field === "string";
  return (
    typeof message.id === "number" &&
    typeof message.at === "string" &&
    (message.tone === "success" || message.tone === "refusal") &&
    typeof message.sentence === "string" &&
    optional(message.detail) &&
    optional(message.object) &&
    optional(message.reference) &&
    isScreen(message.screen)
  );
}

/** What the storage of the tab kept; nothing when it is refused, or holds something else. */
function restored(): MessageHistory {
  try {
    const value: unknown = JSON.parse(window.sessionStorage.getItem(MESSAGES_KEY) ?? "null");
    if (typeof value !== "object" || value === null) {
      return NO_MESSAGES;
    }
    const { messages, seen } = value as Partial<Record<keyof MessageHistory, unknown>>;
    if (!Array.isArray(messages) || typeof seen !== "number") {
      return NO_MESSAGES;
    }
    return { messages: messages.filter(isMessage), seen };
  } catch {
    return NO_MESSAGES;
  }
}

/** Keep the history in the storage of the tab; refused — a quota, a private window —, a reload loses it. */
function keep(kept: MessageHistory): void {
  try {
    if (kept.messages.length === 0) {
      window.sessionStorage.removeItem(MESSAGES_KEY);
    } else {
      window.sessionStorage.setItem(MESSAGES_KEY, JSON.stringify(kept));
    }
  } catch {
    // Refused: the history goes on in the page.
  }
}

/** Change the history, keep it, and tell those who listen. */
function change(next: MessageHistory): void {
  history = next;
  keep(next);
  for (const listener of listeners) {
    listener();
  }
}

/** The history of the session, the same object as long as nothing changes it. */
export function readMessages(): MessageHistory {
  history ??= restored();
  return history;
}

/** Listen to the changes of the history; what it gives back stops listening. */
export function onMessages(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The screen shown, as the browser shows it, with the project it shows when there is one. */
export function shownScreen(project: string | undefined): MessageScreen {
  const { pathname, search } = window.location;
  return { href: `${pathname}${search}`, project };
}

/**
 * Note the outcome a notice told, once: `source` is the outcome itself — the same object however
 * often it is rendered —, and an outcome noted already notes nothing more. `parts` are the parts of
 * it another notice tells — the rest of a refusal said at its fields, told under the form —: noted
 * with it, the other notice notes nothing more.
 */
export function noteMessage(
  source: object,
  draft: MessageDraft,
  project?: string,
  parts: readonly (object | undefined)[] = [],
): void {
  if (noted.has(source)) {
    return;
  }
  noted.add(source);
  for (const part of parts) {
    if (part !== undefined) {
      noted.add(part);
    }
  }
  const { messages, seen } = readMessages();
  const message: Message = {
    id: (messages.at(-1)?.id ?? 0) + 1,
    at: new Date().toISOString(),
    tone: draft.tone,
    sentence: draft.sentence,
    detail: draft.detail,
    object: draft.object,
    reference: draft.reference,
    screen: draft.screen ?? shownScreen(project),
  };
  change({ messages: [...messages, message].slice(-MESSAGES_KEPT), seen });
}

/** The refusals the panel has not shown yet. */
export function unreadRefusals({ messages, seen }: MessageHistory): number {
  return messages.filter((message) => message.tone === "refusal" && message.id > seen).length;
}

/** The panel has shown every message: none is unread. */
export function markMessagesSeen(): void {
  const current = readMessages();
  const last = current.messages.at(-1)?.id ?? 0;
  if (last !== current.seen) {
    change({ ...current, seen: last });
  }
}

/** Forget the history of the session: signing out leaves nothing of it to the next user. */
export function forgetMessages(): void {
  noted = new WeakSet();
  change(NO_MESSAGES);
}

/**
 * Note in the history the outcome a notice tells, once told — `source` its identity, `draft` what
 * to note of it, nothing while the notice tells nothing —, with the project the screen shows.
 */
export function useNoteMessage(
  source: object | undefined,
  draft: MessageDraft | undefined,
  project?: () => string | undefined,
): void {
  useEffect(() => {
    if (source !== undefined && draft !== undefined) {
      noteMessage(source, draft, project?.());
    }
  }, [source, draft, project]);
}
