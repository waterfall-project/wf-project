// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a session leaves to the next in the tab, and the one place that wipes it (#1180): the
 * tasks followed (`wf_background_tasks`) and the history of the messages (`wf_messages`), kept in
 * the storage of the tab (`sessionStorage`), which names objects of the account that wrote them.
 *
 * `wipeStores` is that place. It is called on signing out (`forget` of the tracker of the shell),
 * whenever the session is found ended — a sign-in offered because the session expired or was
 * closed (`useEndedSession`, called by `SignIn`) —, and when the tab shows an account other than
 * the one that wrote the stores. They keep that account's identifier with them
 * (`wf_session_owner`): stores without an owner, or of another, are not the account's to read, so
 * that whatever a page still writes once its session is found ended is wiped at the next load.
 */
"use client";

import { useEffect } from "react";

import { forgetMessages } from "@/components/notices/message-history";

import { forgetTasks } from "./storage";

/** The key of the storage of the tab under which the account that wrote the stores is kept. */
export const OWNER_KEY = "wf_session_owner";

/** Whether the stores of the tab were written by this account: the same identifier kept with them. */
export function isOwner(account: string): boolean {
  try {
    return window.sessionStorage.getItem(OWNER_KEY) === account;
  } catch {
    return false;
  }
}

/** Keep the account that writes the stores of the tab from now on. */
export function keepOwner(account: string): void {
  try {
    window.sessionStorage.setItem(OWNER_KEY, account);
  } catch {
    // Refused — a private window —: the stores are refused as well, nothing is left to the next.
  }
}

/**
 * Wipe what a session leaves in the tab: the tasks followed, the history of the messages, and the
 * account that wrote them. The one place that does; the follow-up in the page is the tracker's.
 */
export function wipeStores(): void {
  forgetTasks();
  forgetMessages();
  try {
    window.sessionStorage.removeItem(OWNER_KEY);
  } catch {
    // Refused — a private window —: nothing was kept.
  }
}

/** Wipe the stores of the tab once mounted: used where the session is found ended. */
export function useEndedSession(): void {
  useEffect(() => {
    wipeStores();
  }, []);
}
