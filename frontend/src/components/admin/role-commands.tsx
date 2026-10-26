// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the table of the access roles (US-0380, #380), for a session that may modify them
 * (`access_roles.write`): a role created in line from its label alone — its permissions are written
 * in the matrix —, and deleted from its row once the deletion is confirmed — a logical deletion
 * (#456), which nothing restores, a predefined role included: a role created again is never
 * predefined —, unavailable while an account holds it, as the server would refuse it
 * (`ACCESS_ROLE_IN_USE`, WF-ADM-0090); its renaming is the entry of its label (`admin-grids.tsx`).
 * What a write did is said in the region of the table, named after it; a refusal, above it by the
 * catalogue of the codes of error, on the reading it was asked from alone (`Reactivations`). The
 * roles answered are shared with the matrix (`RoleAnswers`). Every prop is data, never a function
 * (défaut n° 12 de `typescript.md`).
 */
"use client";

import { Plus, Trash2, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";

import { createAccessRole, deleteAccessRole } from "@/api/actions/access-roles";
import type { components } from "@/api/generated/schema";
import { UNAVAILABLE } from "@/components/commands/offer";
import { useNoteRefusal } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { parsedEntry } from "@/components/grid/cell-values";
import { useSaid } from "@/components/notices/said";
import { CellCommand } from "@/components/reference/cell-command";
import { Reactivations, useListReport } from "@/components/reference/reactivation";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { problemMessage } from "@/i18n/problem";

import { LABEL_LENGTH, ROLE_READS } from "./role-address";
import { RoleAnswers } from "./role-answers";

type AccessRole = components["schemas"]["AccessRole"];

/** How a command of the table says what it did; none outside the table. */
const Say = createContext<((text: string) => void) | undefined>(undefined);

/** How the deletion of a role is asked, and the roles whose deletion is under way. */
interface Deletions {
  readonly ask: (role: AccessRole) => void;
  readonly deleting: ReadonlySet<string>;
}

/** The deletions of the table; none outside it. */
const DeletionsContext = createContext<Deletions | undefined>(undefined);

/**
 * The commands of the table: the region that says what the last one did — rendered from the start,
 * so that a reader of the screen hears what is put in it, and named after the table —, the
 * confirmation of a deletion, and the refusals told above the table.
 */
export function RoleCommands({ children }: { readonly children: ReactNode }) {
  const t = useTranslations("admin.accessRoles");
  // What the last write said, and the how-many-th it was, noted in the history of the messages.
  const [said, say] = useSaid();
  return (
    <RoleAnswers>
      <Reactivations reads={ROLE_READS}>
        <p
          role="status"
          aria-live="polite"
          aria-label={t("told")}
          className="min-h-5 text-sm text-muted-foreground"
        >
          {said === undefined ? null : <span key={said.count}>{said.text}</span>}
        </p>
        <Say value={say}>
          <Deletion>{children}</Deletion>
        </Say>
      </Reactivations>
    </RoleAnswers>
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
  // The role whose deletion is asked — kept while the confirmation closes —, and whether it is open.
  const [asked, setAsked] = useState<{ readonly role: AccessRole; readonly open: boolean }>();
  const [deleting, setDeleting] = useState<ReadonlySet<string>>(() => new Set());
  const ask = useCallback((role: AccessRole) => {
    setAsked({ role, open: true });
  }, []);
  const deletions = useMemo(() => ({ ask, deleting }), [ask, deleting]);
  const confirmed = (role: AccessRole) => {
    const id = role.access_role_id;
    // The reading the role is deleted from: its refusal is told on it alone.
    const generation = list?.generation ?? 0;
    setDeleting((before) => new Set(before).add(id));
    void deleteAccessRole(id)
      .catch(rejected)
      .then((outcome) => {
        setDeleting((before) => {
          const after = new Set(before);
          after.delete(id);
          return after;
        });
        if (outcome.kind === "done") {
          say?.(t("deleted", { name: role.label }));
        } else {
          list?.report({ outcome, generation, names: {}, target: `delete ${id}` });
        }
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
 * The creation of a role in line, at the head of the table: its label, which the contract bounds,
 * then the command. A label left blank is refused at its field as the entry of the grid refuses it
 * (`parsedEntry`), nothing asked; the label typed stays until the server answers; a role created
 * empties it, unless another was typed meanwhile. The label the server refuses (422, `/label`) is
 * said at its field, which takes the focus; any other refusal, above the table.
 */
export function CreateRole() {
  const t = useTranslations("admin.accessRoles");
  const locale = useLocale();
  const messages = useMessages();
  const say = useContext(Say);
  const list = useListReport();
  const [label, setLabel] = useState("");
  const [refused, setRefused] = useState<string>();
  const noteRefusal = useNoteRefusal();
  const [pending, startTransition] = useTransition();
  // Asked anew at each refusal: the field takes the focus after the commit that says its refusal,
  // described by it as it is heard (#1484).
  const [focused, setFocused] = useState<object>();
  const input = useRef<HTMLInputElement>(null);
  const field = useId();
  useEffect(() => {
    if (focused !== undefined) {
      input.current?.focus();
    }
  }, [focused]);
  return (
    <form
      aria-label={t("creation")}
      className="flex flex-wrap items-center gap-2"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        if (pending) {
          return;
        }
        const parsed = parsedEntry({ type: "text", maxLength: LABEL_LENGTH }, label, locale);
        if ("problem" in parsed) {
          const code = parsed.problem === "required" ? "VALUE_REQUIRED" : "VALUE_TOO_LONG";
          setRefused(problemMessage({ code }, { locale, messages }));
          setFocused({});
          return;
        }
        // The reading the role is created from: its refusal is told on it alone.
        const generation = list?.generation ?? 0;
        const asked = label;
        setRefused(undefined);
        startTransition(async () => {
          const outcome = await createAccessRole({ label: asked, permissions: [] }).catch(rejected);
          if (outcome.kind === "done") {
            setLabel((typed) => (typed === asked ? "" : typed));
            say?.(t("created", { name: outcome.data.label }));
            return;
          }
          const at = "problem" in outcome ? outcome.problem.fields : undefined;
          const own = at?.find(({ pointer }) => pointer === "/label");
          if (own === undefined) {
            list?.report({ outcome, generation, names: {} });
            return;
          }
          // Said at its field, out of a notice: noted in the history of the messages.
          noteRefusal(outcome, { subject: asked });
          setRefused(problemMessage(own, { locale, messages }));
          setFocused({});
        });
      }}
    >
      <Label htmlFor={field} className="text-sm whitespace-nowrap">
        {t("newLabel")}
      </Label>
      <Input
        ref={input}
        id={field}
        value={label}
        required
        maxLength={LABEL_LENGTH}
        autoComplete="off"
        aria-invalid={refused === undefined ? undefined : true}
        aria-describedby={refused === undefined ? undefined : `${field}-refused`}
        className="h-8 w-60"
        onChange={(event) => {
          setLabel(event.target.value);
        }}
      />
      <Button type="submit" variant="outline" size="sm" aria-busy={pending}>
        <Plus aria-hidden="true" />
        {t("create")}
      </Button>
      {refused === undefined ? null : (
        <p id={`${field}-refused`} className="text-sm text-destructive">
          {refused}
        </p>
      )}
    </form>
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
  const pending = deletions?.deleting.has(role.access_role_id) ?? false;
  return (
    <CellCommand
      label={name}
      help={said("deleteRole.help")}
      unavailable={held}
      aria-busy={pending}
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
