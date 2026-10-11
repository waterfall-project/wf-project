// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The roles the server answered a write with, until the page read anew holds them (US-0380): one
 * source for the table, whose renaming writes from it (`admin-grids.tsx`), and for the matrix of the
 * permissions, whose cells show and write from it (`permission-matrix.tsx`) — a role renamed, then a
 * cell of it checked before the page is read anew, goes from the version the renaming answered, and
 * the other way round. The role answered prevails over the same role read while it is newer, by its
 * counter (`lock_version`); a role read since, as new or newer, prevails over it (défaut n° 22 de
 * `typescript.md`).
 */
"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

import type { AccessRole, RoleAnswered } from "./admin-grids";

/** The newer of a role read and the same role answered, by its counter. */
export function newer(read: AccessRole, answered: AccessRole | undefined): AccessRole {
  return answered !== undefined && answered.lock_version > read.lock_version ? answered : read;
}

/** The roles answered, read in a render, and how to read and record them in an event. */
interface Answers extends RoleAnswered {
  /** The roles answered, by their identifier, as the last render saw them. */
  readonly answered: ReadonlyMap<string, AccessRole>;
}

const AnswersContext = createContext<Answers | undefined>(undefined);

/** The roles answered of the screen; none outside a screen whose roles are written. */
export function useRoleAnswers(): Answers | undefined {
  return useContext(AnswersContext);
}

/**
 * Share the roles the server answered among the table and the matrix of a screen: those shared
 * around are kept — the screen's, which the table and the matrix share —, so that each part may
 * hold its own when nothing is shared around it.
 */
export function RoleAnswers({ children }: { readonly children: ReactNode }) {
  const around = useContext(AnswersContext);
  const [answered, setAnswered] = useState<ReadonlyMap<string, AccessRole>>(() => new Map());
  // The same, as the last answer left them: an event reads it, which may run before the render.
  const latestAnswers = useRef<ReadonlyMap<string, AccessRole>>(answered);
  const record = useCallback((role: AccessRole) => {
    const id = role.access_role_id;
    const kept = latestAnswers.current.get(id);
    if (kept !== undefined && kept.lock_version >= role.lock_version) {
      return;
    }
    const next = new Map(latestAnswers.current).set(id, role);
    latestAnswers.current = next;
    setAnswered(next);
  }, []);
  const latest = useCallback(
    (read: AccessRole) => newer(read, latestAnswers.current.get(read.access_role_id)),
    [],
  );
  const value = useMemo(() => ({ answered, latest, record }), [answered, latest, record]);
  return <AnswersContext value={around ?? value}>{children}</AnswersContext>;
}
