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
 *
 * The roles being written are kept beside them: a renaming, a cell of the matrix and a confirmed
 * deletion each mark their role until the server answers, whatever the answer, and the label, the
 * cells and « Supprimer » of a role so marked are busy and send nothing — the next write goes from the
 * role answered, never from the version a write under way is about to leave (US-1780, #2261).
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
  /** The roles being written, by their identifier, as the last render saw them. */
  readonly writing: ReadonlySet<string>;
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
  const [writing, setWriting] = useState<ReadonlySet<string>>(() => new Set());
  // The same, as the last mark left them: an event reads it, which may run before the render.
  const latestWriting = useRef<ReadonlySet<string>>(writing);
  const isWriting = useCallback((id: string) => latestWriting.current.has(id), []);
  const begin = useCallback((id: string) => {
    const next = new Set(latestWriting.current).add(id);
    latestWriting.current = next;
    setWriting(next);
  }, []);
  const end = useCallback((id: string) => {
    const next = new Set(latestWriting.current);
    next.delete(id);
    latestWriting.current = next;
    setWriting(next);
  }, []);
  const value = useMemo(
    () => ({ answered, writing, latest, record, isWriting, begin, end }),
    [answered, writing, latest, record, isWriting, begin, end],
  );
  return <AnswersContext value={around ?? value}>{children}</AnswersContext>;
}

/**
 * The label of a role in its cell of the table: busy, and out of any entry, while a write of the
 * role is under way (`RoleAnswers`).
 */
export function RoleLabelCell({ role }: { readonly role: AccessRole }) {
  const busy = useRoleAnswers()?.writing.has(role.access_role_id) === true;
  return (
    <span aria-busy={busy} aria-disabled={busy ? true : undefined}>
      {role.label}
    </span>
  );
}
