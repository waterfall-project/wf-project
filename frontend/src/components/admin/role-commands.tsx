// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the table of the access roles (US-0380, #380), for a session that may modify them
 * (`access_roles.write`): a role created from its label alone, in the dialog that « Nouveau rôle »
 * opens (`role-creation.tsx`) — its permissions are written in the matrix —, and deleted from its row once the deletion is confirmed — a logical deletion
 * (#456), which nothing restores, a predefined role included: a role created again is never
 * predefined —, unavailable while an account holds it, as the server would refuse it
 * (`ACCESS_ROLE_IN_USE`, WF-ADM-0090); its renaming is the entry of its label (`admin-grids.tsx`).
 * What a write did is said in the region of the table, named after it; a refusal, above it by the
 * catalogue of the codes of error, on the reading it was asked from alone (`Reactivations`). The
 * roles answered are shared with the matrix (`RoleAnswers`). The navigations of the page wait for
 * each write, and do not take place when it is refused (`held` of the list, #688). Every prop is
 * data, never a function (défaut n° 12 de `typescript.md`).
 */
"use client";

import { Plus, Trash2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";

import { deleteAccessRole } from "@/api/actions/access-roles";
import type { components } from "@/api/generated/schema";
import { useHeldCommand } from "@/components/commands/held";
import { UNAVAILABLE } from "@/components/commands/offer";
import { rejectedWrite } from "@/components/commands/rejection";
import { type Said, useSaid } from "@/components/notices/said";
import { CellCommand } from "@/components/reference/cell-command";
import { useListReading } from "@/components/reference/list-reading";
import { Reactivations, useListReport } from "@/components/reference/reactivation";
import type { PrincipalVariant } from "@/components/shell/section-card";
import { useRaise } from "@/components/system/raise";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

import { ROLE_READS } from "./role-address";
import { RoleAnswers, useRoleAnswers } from "./role-answers";
import { RoleCreation } from "./role-creation";

type AccessRole = components["schemas"]["AccessRole"];

/** How a command of the table says what it did; none outside the table. */
const Say = createContext<((text: string) => void) | undefined>(undefined);

/** How the deletion of a role is asked; the roles being written are those of `RoleAnswers`. */
interface Deletions {
  readonly ask: (role: AccessRole) => void;
}

/** The deletions of the table; none outside it. */
const DeletionsContext = createContext<Deletions | undefined>(undefined);

/**
 * The commands of the table: the region that says what the last one did — rendered from the start,
 * so that a reader of the screen hears what is put in it, and named after the table —, the
 * confirmation of a deletion, and the refusals told above the table.
 */
export function RoleCommands({ children }: { readonly children: ReactNode }) {
  // What the last write said, and the how-many-th it was, noted in the history of the messages.
  const [said, say] = useSaid();
  return (
    <RoleAnswers>
      <Reactivations reads={ROLE_READS}>
        <Say value={say}>
          <Creation said={said}>
            <Deletion>{children}</Deletion>
          </Creation>
        </Say>
      </Reactivations>
    </RoleAnswers>
  );
}

/** The opening of the creation: the command that opened it, which takes the focus back. */
interface Opening {
  readonly trigger: HTMLElement;
}

/** What opens the creation of a role, and what the table last said. */
interface Creations {
  readonly open: (trigger: HTMLElement) => void;
  readonly said: Said | undefined;
}

/** The creation of the table; none outside it. */
const CreationsContext = createContext<Creations | undefined>(undefined);

/** The dialog of the creation of a role, rendered while the command has opened it. */
function Creation({
  said,
  children,
}: {
  readonly said: Said | undefined;
  readonly children: ReactNode;
}) {
  const t = useTranslations("admin.accessRoles");
  const say = useContext(Say);
  const list = useListReport();
  const [creating, setCreating] = useState<Opening>();
  const creations = useMemo(
    () => ({
      open: (trigger: HTMLElement) => {
        setCreating({ trigger });
      },
      said,
    }),
    [said],
  );
  return (
    <CreationsContext value={creations}>
      {children}
      {creating === undefined ? null : (
        <RoleCreation
          onCreated={(role) => {
            say?.(t("created", { name: role.label }));
          }}
          onClose={() => {
            setCreating((current) => (current === creating ? undefined : current));
          }}
          onClosed={() => {
            if (creating.trigger.isConnected) {
              creating.trigger.focus();
            } else {
              list?.refocus();
            }
          }}
        />
      )}
    </CreationsContext>
  );
}

/**
 * The deletion of the roles of the table: asked from a row, it opens a confirmation that names the
 * role and says the deletion is final — Escape or « Conserver » gives it up, nothing deleted —;
 * confirmed, the server is asked, and the row says it is under way until it answers. Outside the
 * grid, so that no key pressed in the confirmation reaches the grid; closed, the focus goes back to
 * the active cell of the grid.
 */
function Deletion({ children }: { readonly children: ReactNode }) {
  const t = useTranslations("admin.accessRoles");
  const say = useContext(Say);
  const list = useListReport();
  // The list, which tells the refusal, holds the navigations while the deletion answers: the
  // confirmation is closed meanwhile (#688, #889).
  const own = useHeldCommand();
  const held = list?.held ?? own;
  // The role whose deletion is asked — kept while the confirmation closes —, and whether it is open.
  const [asked, setAsked] = useState<{ readonly role: AccessRole; readonly open: boolean }>();
  const answers = useRoleAnswers();
  const raise = useRaise();
  // A write of the list lost once sent: the list is read anew, and this waits until it is back (US-2240).
  const reading = useListReading();
  const ask = useCallback((role: AccessRole) => {
    setAsked({ role, open: true });
  }, []);
  const deletions = useMemo(() => ({ ask }), [ask]);
  const confirmed = (shown: AccessRole) => {
    // The role as the screen holds it now: a write of it may have answered since the confirmation
    // opened, and one under way is answered first.
    const role = answers?.latest(shown) ?? shown;
    const id = role.access_role_id;
    if (answers?.isWriting(id) === true || reading) {
      return;
    }
    // The reading the role is deleted from: its refusal is told on it alone.
    const generation = list?.generation ?? 0;
    answers?.begin(id);
    // A command that rejects, though the hold catches the rejections of the action: told as the
    // commands tell a rejected action; and what the telling itself throws is raised to the screen
    // of failure, never left unhandled (#3111).
    void held(deleteAccessRole(id, role.lock_version))
      .catch(rejectedWrite())
      .then((outcome) => {
        if (outcome.kind === "done") {
          say?.(t("deleted", { name: role.label }));
        } else {
          list?.report({ outcome, generation, names: {}, target: `delete ${id}` });
        }
      })
      .catch(raise)
      .finally(() => {
        // Whatever the answer, a rejection included: the role is free again (#2898).
        answers?.end(id);
      });
  };
  const name = asked?.role.label ?? "";
  return (
    <>
      <DeletionsContext value={deletions}>{children}</DeletionsContext>
      <AlertDialog
        open={asked?.open ?? false}
        onOpenChange={(open) => {
          if (!open) {
            setAsked((before) => (before === undefined ? before : { ...before, open }));
          }
        }}
      >
        <AlertDialogContent
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            list?.refocus();
          }}
        >
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deletionTitle", { name })}</AlertDialogTitle>
            <AlertDialogDescription>{t("deletionFinal", { name })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>
              <X aria-hidden="true" />
              {t("keep")}
            </AlertDialogCancel>
            <AlertDialogAction
              // A write of the role under way is answered first: the confirmation stays open, and
              // its command busy, rather than closing on a press that sends nothing.
              disabled={reading || answers?.writing.has(asked?.role.access_role_id ?? "") === true}
              onClick={() => {
                if (asked !== undefined) {
                  confirmed(asked.role);
                }
              }}
            >
              <Trash2 aria-hidden="true" />
              {t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

/**
 * The command that opens the creation of a role, at the right of the title of the card of the roles
 * — the principal command of the card, which draws it at its variant —, after the region that says
 * what the last write of the table did, rendered from the start so that a reader of the screen
 * hears what is put in it, and taking no room while it says nothing.
 */
export function CreateRole({ variant = "outline" }: { readonly variant?: PrincipalVariant }) {
  const t = useTranslations("admin.accessRoles");
  const creations = useContext(CreationsContext);
  const said = creations?.said;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <p
        role="status"
        aria-live="polite"
        aria-label={t("told")}
        className="text-sm text-muted-foreground empty:sr-only"
      >
        {said === undefined ? null : <span key={said.count}>{said.text}</span>}
      </p>
      <Button
        type="button"
        variant={variant}
        size="sm"
        aria-haspopup="dialog"
        onClick={(event) => {
          creations?.open(event.currentTarget);
        }}
      >
        <Plus aria-hidden="true" />
        {t("newLabel")}
      </Button>
    </div>
  );
}

/**
 * The deletion of a role, named after it: unavailable while an account holds it, as the server would
 * refuse it, with the condition it lacks; available, it asks for the confirmation of the table.
 */
export function DeleteRole({ role }: { readonly role: AccessRole }) {
  const t = useTranslations("admin.accessRoles");
  const told = useTranslations("admin.commands");
  const said = useTranslations("commands");
  const say = useContext(Say);
  const deletions = useContext(DeletionsContext);
  const name = t("deleteRole", { name: role.label });
  const held = role.holder_count > 0 ? t("heldBy", { count: role.holder_count }) : undefined;
  // Any write of the role under way, a renaming or a cell of the matrix as well as its deletion.
  const pending = useRoleAnswers()?.writing.has(role.access_role_id) === true;
  return (
    <CellCommand
      label={name}
      help={said("deleteRole.help")}
      aria-haspopup="dialog"
      unavailable={held}
      aria-busy={pending}
      waiting={pending}
      className={UNAVAILABLE}
      onClick={() => {
        if (held !== undefined) {
          // An unavailable command never runs: the press says the condition it lacks.
          say?.(told("unmet", { command: name, condition: held }));
          return;
        }
        if (!pending) {
          deletions?.ask(role);
        }
      }}
    >
      <Trash2 aria-hidden="true" />
      {t("delete")}
    </CellCommand>
  );
}
