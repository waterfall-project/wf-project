// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the table of the accounts (US-0360, #379), for a session that may modify them
 * (`users.write`): the table is its own entry — the names of a local account in their cells
 * (`admin-grids.tsx`), its state on a switch, its access roles in a list of several choices, the link
 * by which its holder sets a password and the anonymisation of a deactivated one (`user-cells.tsx`) —,
 * and « Créer un compte local » heads it (`user-dialogs.tsx`). No command deletes an account
 * (WF-ADM-0060).
 *
 * The accounts the server answered a write with are kept here until the page read anew holds them,
 * one source for every cell of a row: the account answered prevails over the same account read while
 * it is newer, by its counter (`lock_version`), and the next write of the row, whatever its cell,
 * goes from its version (défaut n° 22 de `typescript.md`). The writes of a row go one after the
 * other: a name entered while another write of its row is under way waits for its answer, and goes
 * from the version it answered; the switch, the roles and the anonymisation of the row are marked busy
 * and unavailable the while. What a write asked shows until the server answers. The anonymisation,
 * irreversible, is confirmed first, in a dialog outside the grid that names the account and says so
 * (`AnonymizationDialog`), as the deletion of a role is. What a write did is said in the region of
 * the table, named after it, as the condition an unavailable command lacks; a refusal of the switch,
 * of the roles, of the anonymisation or of the link, above it by the catalogue of the codes of error,
 * on the reading it was asked from alone (`Reactivations`, défaut n° 1), that of a name, at its cell.
 * Every prop is data, never a function (défaut n° 12).
 */
"use client";

import { UserPlus } from "lucide-react";
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

import { anonymizeUser, createPasswordSetupLink, resendInvitation } from "@/api/actions/users";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { useAccountNaming } from "@/components/account/account-name";
import { rejected } from "@/components/commands/rejection";
import { type Say, useSaid } from "@/components/notices/said";
import { Reactivations, useListReport } from "@/components/reference/reactivation";
import { Button } from "@/components/ui/button";

import type { User } from "./admin-grids";
import { AnonymizationDialog, SetupLinkDialog, UserCreation } from "./user-dialogs";
import { USER_READS } from "./user-address";

/** A link to set a password, as the contract gives it. */
type SetupLink = components["schemas"]["PasswordSetupLink"];

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

/** A write of an account sent once the writes of its row under way are answered. */
export interface QueuedWrite {
  /** Send the write from the account as the writes before it left it. */
  readonly send: (user: User) => Promise<Outcome<User>>;
  readonly said: (answered: User) => string;
}

/** The accounts of the table as they show, and the commands that change them. */
export interface UserWrites {
  /** The accounts answered, by their identifier, as the last render saw them. */
  readonly answered: ReadonlyMap<string, User>;
  /** What the writes of the switch or of the roles under way asked, by account. */
  readonly asked: ReadonlyMap<string, Asked>;
  /** The accounts a write of which, whatever its cell, is under way. */
  readonly busy: ReadonlySet<string>;
  /** The account as it stands now: the one last answered, or the one read when it is as new. */
  readonly latest: (read: User) => User;
  /** Write an account by its switch or its roles, unless a write of it is under way. */
  readonly run: (shown: User, write: UserWrite) => void;
  /**
   * Write an account once the writes of its row under way are answered — a name entered —, its
   * answer kept and said; its outcome given back, for the cell to tell a refusal.
   */
  readonly queue: (shown: User, write: QueuedWrite) => Promise<Outcome<User>>;
  /** Open the creation of a local account, from the command pressed. */
  readonly create: (trigger: HTMLElement) => void;
  /**
   * Ask the link of an account, from the command pressed, and show it once given; nothing while
   * another link is asked or shown.
   */
  readonly giveLink: (user: User, name: string, trigger: HTMLElement) => void;
  /** Whether a link is asked or shown: every command of the link waits until it is closed. */
  readonly linking: boolean;
  /**
   * Have the identity provider send again the email of the link of an account (`resendInvitation`),
   * and say that it went; a refusal — no email leaves an installation without a mail server, 503 —
   * is told on the reading it was asked from, never as a sent email.
   */
  readonly resend: (user: User, name: string, trigger: HTMLElement) => void;
  /** The accounts whose email is asked and not yet answered. */
  readonly resending: ReadonlySet<string>;
  /** Ask the confirmation of the anonymisation of an account, from the command pressed. */
  readonly anonymize: (user: User, back: HTMLElement | null) => void;
  /** Say in the region of the table what a command did, or the condition it lacks. */
  readonly say: Say;
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
    <Reactivations reads={USER_READS} fill>
      <Writes>{children}</Writes>
    </Reactivations>
  );
}

/**
 * An opening of the creation, from the command pressed: each its own, so that a dialog closes its
 * opening alone, never one opened since.
 */
interface Opening {
  readonly trigger: HTMLElement;
}

/** A link given, the account it is for, and the command that asked it. */
interface Given {
  readonly link: SetupLink;
  readonly name: string;
  readonly trigger: HTMLElement;
}

/** An account whose anonymisation is asked, the command that asked it, and whether it is open. */
interface Anonymizing {
  readonly user: User;
  readonly back: HTMLElement | null;
  readonly open: boolean;
}

/** Give the focus back to a command, or to its cell in the grid; to the list when it is gone. */
function focusBack(trigger: HTMLElement, list: (() => void) | undefined) {
  if (!trigger.isConnected) {
    list?.();
    return;
  }
  (trigger.closest<HTMLElement>("td") ?? trigger).focus();
}

/**
 * The accounts answered and asked, the region that says what the last write did — rendered from the
 * start, so that a reader of the screen hears what is put in it —, the creation of an account and the
 * link given.
 */
function Writes({ children }: { readonly children: ReactNode }) {
  const t = useTranslations("admin.users");
  const list = useListReport();
  const naming = useAccountNaming();
  // What the last write did, noted in the history of the messages as it is said.
  const [said, say] = useSaid();
  const [answered, setAnswered] = useState<ReadonlyMap<string, User>>(() => new Map());
  // The same, as the last answer left them: an event reads it, which may run before the render.
  const latestAnswers = useRef<ReadonlyMap<string, User>>(answered);
  const [asked, setAsked] = useState<ReadonlyMap<string, Asked>>(() => new Map());
  const [busy, setBusy] = useState<ReadonlySet<string>>(() => new Set());
  // The last write of each row under way, settled whatever its outcome: the next one waits for it.
  const asking = useRef(new Map<string, Promise<unknown>>());
  const [creating, setCreating] = useState<Opening>();
  const [given, setGiven] = useState<Given>();
  const [linking, setLinking] = useState(false);
  const [resending, setResending] = useState<ReadonlySet<string>>(() => new Set());
  // The same, as the last press left it: two presses may come before a render.
  const resendHeld = useRef(new Set<string>());
  // The same, as the last press left it: two presses may come before a render.
  const linkHeld = useRef(false);
  // The account whose anonymisation is asked — kept while the confirmation closes —, and whether
  // the confirmation is open.
  const [anonymizing, setAnonymizing] = useState<Anonymizing>();

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
  // Send a write of a row once those before it are answered, from the account as they left it; the
  // row busy until its last write is answered.
  const reserve = useCallback(
    (shown: User, write: QueuedWrite): Promise<Outcome<User>> => {
      const id = shown.user_id;
      const before = asking.current.get(id) ?? Promise.resolve();
      const sent = before.then(async () => {
        const outcome = await write.send(latest(shown));
        if (outcome.kind === "done") {
          record(outcome.data);
          say(write.said(outcome.data), { object: naming.person(outcome.data) });
        }
        return outcome;
      });
      const settled = sent.then(
        () => undefined,
        () => undefined,
      );
      asking.current.set(id, settled);
      setBusy((rows) => (rows.has(id) ? rows : new Set(rows).add(id)));
      void settled.then(() => {
        if (asking.current.get(id) !== settled) {
          return;
        }
        asking.current.delete(id);
        setBusy((rows) => {
          const after = new Set(rows);
          after.delete(id);
          return after;
        });
      });
      return sent;
    },
    [latest, record, say, naming],
  );
  const run = useCallback(
    (shown: User, write: UserWrite) => {
      const id = shown.user_id;
      if (asking.current.has(id)) {
        return;
      }
      setAsked((before) => new Map(before).set(id, write.asked));
      // The reading the row is written on: its refusal is told on it alone.
      const generation = list?.generation ?? 0;
      void reserve(shown, { send: (user) => write.send(user).catch(rejected), said: write.said })
        .catch(rejected)
        .then((outcome) => {
          setAsked((before) => {
            const after = new Map(before);
            after.delete(id);
            return after;
          });
          if (outcome.kind !== "done") {
            list?.report({
              outcome,
              generation,
              names: {},
              target: write.target,
              back: write.back,
            });
          }
        });
    },
    [list, reserve],
  );
  const releaseLink = useCallback(() => {
    linkHeld.current = false;
    setLinking(false);
  }, []);
  const giveLink = useCallback(
    (user: User, name: string, trigger: HTMLElement) => {
      if (linkHeld.current) {
        // One link at a time: the one asked or shown is closed first.
        return;
      }
      linkHeld.current = true;
      setLinking(true);
      const id = user.user_id;
      // The reading the link is asked from: its refusal is told on it alone.
      const generation = list?.generation ?? 0;
      void createPasswordSetupLink(id)
        .catch(rejected)
        .then((outcome) => {
          if (outcome.kind === "done") {
            setGiven({ link: outcome.data, name, trigger });
          } else {
            releaseLink();
            list?.report({ outcome, generation, names: {}, target: `link ${id}`, back: trigger });
          }
        });
    },
    [list, releaseLink],
  );
  const resend = useCallback(
    (user: User, name: string, trigger: HTMLElement) => {
      const id = user.user_id;
      if (resendHeld.current.has(id)) {
        return;
      }
      resendHeld.current.add(id);
      setResending(new Set(resendHeld.current));
      const generation = list?.generation ?? 0;
      void resendInvitation(id)
        .catch(rejected)
        .then((outcome) => {
          resendHeld.current.delete(id);
          setResending(new Set(resendHeld.current));
          if (outcome.kind === "done") {
            say(t("resent", { name }), { object: name });
          } else {
            list?.report({
              outcome,
              generation,
              names: {},
              target: `invitation ${id}`,
              back: trigger,
            });
          }
        });
    },
    [list, say, t],
  );
  const create = useCallback((trigger: HTMLElement) => {
    setCreating({ trigger });
  }, []);
  const anonymize = useCallback((user: User, back: HTMLElement | null) => {
    setAnonymizing({ user, back, open: true });
  }, []);
  const writes = useMemo<UserWrites>(
    () => ({
      answered,
      asked,
      busy,
      latest,
      run,
      queue: reserve,
      create,
      giveLink,
      linking,
      resend,
      resending,
      anonymize,
      say,
    }),
    [
      answered,
      asked,
      busy,
      latest,
      run,
      reserve,
      create,
      giveLink,
      linking,
      resend,
      resending,
      anonymize,
      say,
    ],
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
      {creating === undefined ? null : (
        <UserCreation
          linking={linking}
          onCreated={(user) => {
            const name = naming.person(user);
            say(t(user.invitation_sent ? "created" : "createdUninvited", { name }), {
              object: name,
            });
          }}
          onLink={(user) => {
            giveLink(user, naming.person(user), creating.trigger);
          }}
          onClose={() => {
            setCreating((current) => (current === creating ? undefined : current));
          }}
          onClosed={() => {
            focusBack(creating.trigger, list?.refocus);
          }}
        />
      )}
      {given === undefined ? null : (
        <SetupLinkDialog
          link={given.link}
          name={given.name}
          onClose={() => {
            setGiven(undefined);
            releaseLink();
          }}
          onClosed={() => {
            focusBack(given.trigger, list?.refocus);
          }}
        />
      )}
      <AnonymizationDialog
        name={anonymizing === undefined ? "" : naming.person(anonymizing.user)}
        open={anonymizing?.open ?? false}
        onConfirm={() => {
          if (anonymizing === undefined) {
            return;
          }
          const { user, back } = anonymizing;
          run(user, {
            target: `anonymize ${user.user_id}`,
            asked: {},
            send: (shown) => anonymizeUser(shown.user_id, { lock_version: shown.lock_version }),
            said: () => t("anonymized"),
            back,
          });
        }}
        onClose={() => {
          setAnonymizing((before) => (before === undefined ? before : { ...before, open: false }));
        }}
        onClosed={() => {
          list?.refocus();
        }}
      />
    </WritesContext>
  );
}

/** The command that opens the creation of a local account, at the head of the table. */
export function CreateUser() {
  const t = useTranslations("admin.users");
  const writes = useUserWrites();
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="self-start"
      onClick={(event) => {
        writes?.create(event.currentTarget);
      }}
    >
      <UserPlus aria-hidden="true" />
      {t("create")}
    </Button>
  );
}
