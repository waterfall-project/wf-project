// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the table of the accounts (US-0360, #379), for a session that may modify them
 * (`users.write`): the table is its own entry — the names of a local account in their cells
 * (`admin-grids.tsx`), its state on a switch, its access roles in a list of several choices
 * (`user-cells.tsx`). No command deletes an account (WF-ADM-0060).
 *
 * The accounts the server answered a write with are kept here until the page read anew holds them,
 * one source for every cell of a row: the account answered prevails over the same account read while
 * it is newer, by its counter (`lock_version`), and the next write of the row, whatever its cell,
 * goes from its version (défaut n° 22 de `typescript.md`). What a write asked shows until the server
 * answers, the row's other writes waiting for it. What a write did is said in the region of the table,
 * named after it; a refusal, above it by the catalogue of the codes of error, on the reading it was
 * asked from alone (`Reactivations`, défaut n° 1). Every prop is data, never a function (défaut
 * n° 12).
 */
"use client";

import { useTranslations } from "next-intl";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

import type { Outcome } from "@/api/problem";
import { rejected } from "@/components/commands/rejection";
import { Reactivations, useListReport } from "@/components/reference/reactivation";

import type { User } from "./admin-grids";
import { USER_READS } from "./user-address";

/** What a write of an account asked, shown until the server answers: its state, or its roles. */
export interface Asked {
  readonly is_active?: boolean;
  readonly access_role_ids?: readonly string[];
}

/** A write of an account from the version the screen holds, and what is said once it is answered. */
export interface UserWrite {
  /** The command and the account, whose refusal a new one of them replaces: `activation <id>`. */
  readonly target: string;
  readonly asked: Asked;
  readonly send: (user: User) => Promise<Outcome<User>>;
  readonly said: (answered: User) => string;
  /** The control that asked it, which takes the focus back once its refusal is dismissed. */
  readonly back: HTMLElement | null;
}

/** The accounts of the table as they show, and the commands that change them. */
export interface UserWrites {
  /** The accounts answered, by their identifier, as the last render saw them. */
  readonly answered: ReadonlyMap<string, User>;
  /** What the writes under way asked, by account. */
  readonly asked: ReadonlyMap<string, Asked>;
  /** The account as it stands now: the one last answered, or the one read when it is as new. */
  readonly latest: (read: User) => User;
  /** Keep an account answered, unless one newer is kept. */
  readonly record: (answered: User) => void;
  /** Write an account, unless a write of it is under way. */
  readonly run: (shown: User, write: UserWrite) => void;
}

const WritesContext = createContext<UserWrites | undefined>(undefined);

/** The writes of the table of the accounts; none outside it, or for a session that may not write. */
export function useUserWrites(): UserWrites | undefined {
  return useContext(WritesContext);
}

/** The newer of an account read and the same account answered, by its counter. */
export function newer(read: User, answered: User | undefined): User {
  return answered !== undefined && answered.lock_version > read.lock_version ? answered : read;
}

/** The commands of the table of the accounts, and the refusals told above it. */
export function UserCommands({ children }: { readonly children: ReactNode }) {
  return (
    <Reactivations reads={USER_READS}>
      <Writes>{children}</Writes>
    </Reactivations>
  );
}

/**
 * The accounts answered and asked, and the region that says what the last write did — rendered
 * from the start, so that a reader of the screen hears what is put in it.
 */
function Writes({ children }: { readonly children: ReactNode }) {
  const t = useTranslations("admin.users");
  const list = useListReport();
  const [said, setSaid] = useState<{ readonly text: string; readonly count: number }>();
  const say = useCallback((text: string) => {
    setSaid((before) => ({ text, count: (before?.count ?? 0) + 1 }));
  }, []);
  const [answered, setAnswered] = useState<ReadonlyMap<string, User>>(() => new Map());
  // The same, as the last answer left them: an event reads it, which may run before the render.
  const latestAnswers = useRef<ReadonlyMap<string, User>>(answered);
  const [asked, setAsked] = useState<ReadonlyMap<string, Asked>>(() => new Map());
  const asking = useRef(new Set<string>());

  const record = useCallback((user: User) => {
    const kept = latestAnswers.current.get(user.user_id);
    if (kept !== undefined && kept.lock_version >= user.lock_version) {
      return;
    }
    const next = new Map(latestAnswers.current).set(user.user_id, user);
    latestAnswers.current = next;
    setAnswered(next);
  }, []);
  const latest = useCallback(
    (read: User) => newer(read, latestAnswers.current.get(read.user_id)),
    [],
  );
  const run = useCallback(
    (shown: User, write: UserWrite) => {
      const user = latest(shown);
      const id = user.user_id;
      if (asking.current.has(id)) {
        return;
      }
      asking.current.add(id);
      setAsked((before) => new Map(before).set(id, write.asked));
      // The reading the row is written on: its refusal is told on it alone.
      const reading = list?.reading ?? "";
      void write
        .send(user)
        .catch(rejected)
        .then((outcome) => {
          asking.current.delete(id);
          setAsked((before) => {
            const after = new Map(before);
            after.delete(id);
            return after;
          });
          if (outcome.kind === "done") {
            record(outcome.data);
            say(write.said(outcome.data));
          } else {
            list?.report({ outcome, reading, names: {}, target: write.target, back: write.back });
          }
        });
    },
    [latest, list, record, say],
  );
  const writes = useMemo<UserWrites>(
    () => ({ answered, asked, latest, record, run }),
    [answered, asked, latest, record, run],
  );
  return (
    <WritesContext value={writes}>
      <p
        role="status"
        aria-live="polite"
        aria-label={t("told")}
        className="min-h-5 text-sm text-muted-foreground"
      >
        {said === undefined ? null : <span key={said.count}>{said.text}</span>}
      </p>
      {children}
    </WritesContext>
  );
}
