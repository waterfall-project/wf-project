// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the table of the access roles (FBS-1.2, US-0380, #380), for a session that may
 * modify them (`access_roles.write`, `platformOffer`): a role created in line, at the head of the
 * table, from its label alone — its permissions are written in the matrix, the place of their
 * modification —, and each role deleted from its row — a logical deletion (#456): the role is no
 * longer read nor attributable (WF-ADM-0090). Its renaming is the entry of its label, in its cell
 * (`admin-grids.tsx`).
 *
 * The deletion of a role an account holds is presented unavailable, as the server would refuse it
 * (`ACCESS_ROLE_IN_USE`, WF-ADM-0090): marked `aria-disabled`, described by its condition, and a
 * press says the condition in the region of the table, without running it. What a write did is said
 * in that region; a refusal of the server is told above the table by the catalogue of the codes of
 * error, on the reading it was asked from alone (`Reactivations`). Every write answered reads the
 * page anew (`access-roles.ts`): a role created is listed where the server retains it.
 *
 * Every prop is data — the role as the list gives it —, never a function: a server component hands
 * them over (défaut n° 12 de `typescript.md`). In a dense grid, a command is out of the order of
 * tabulation, the grid being one stop: Enter on its cell presses it (`CELL_COMMAND`).
 */
"use client";

import { Plus, Trash2 } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useId,
  useRef,
  useState,
  useTransition,
} from "react";

import { createAccessRole, deleteAccessRole } from "@/api/actions/access-roles";
import type { components } from "@/api/generated/schema";
import { UNAVAILABLE } from "@/components/commands/offer";
import { rejected } from "@/components/commands/rejection";
import { CellCommand } from "@/components/reference/cell-command";
import { Reactivations, useListReport } from "@/components/reference/reactivation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { problemMessage } from "@/i18n/problem";

import { LABEL_LENGTH, ROLE_READS } from "./role-address";

type AccessRole = components["schemas"]["AccessRole"];

/** What the last write of the table said, and the how-many-th it was. */
interface Said {
  readonly text: string;
  readonly count: number;
}

/** How a command of the table says what it did; none outside the table. */
const Say = createContext<((text: string) => void) | undefined>(undefined);

/**
 * The commands of the table: the region that says what the last one did — rendered from the start,
 * so that a reader of the screen hears what is put in it —, and the refusals told above the table.
 */
export function RoleCommands({ children }: { readonly children: ReactNode }) {
  const [said, setSaid] = useState<Said>();
  const say = useCallback((text: string) => {
    setSaid((before) => ({ text, count: (before?.count ?? 0) + 1 }));
  }, []);
  return (
    <Reactivations reads={ROLE_READS}>
      <p role="status" aria-live="polite" className="min-h-5 text-sm text-muted-foreground">
        {said === undefined ? null : <span key={said.count}>{said.text}</span>}
      </p>
      <Say value={say}>{children}</Say>
    </Reactivations>
  );
}

/**
 * The creation of a role in line, at the head of the table: its label, which the contract bounds,
 * then the command. The label typed stays until the server answers; a role created empties it,
 * unless another was typed meanwhile. The label the server refuses (422, `/label`) is said at its
 * field, which takes the focus; any other refusal, above the table.
 */
export function CreateRole() {
  const t = useTranslations("admin.accessRoles");
  const locale = useLocale();
  const messages = useMessages();
  const say = useContext(Say);
  const list = useListReport();
  const [label, setLabel] = useState("");
  const [refused, setRefused] = useState<string>();
  const [pending, startTransition] = useTransition();
  const input = useRef<HTMLInputElement>(null);
  const field = useId();
  return (
    <form
      aria-label={t("creation")}
      className="flex flex-wrap items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (pending) {
          return;
        }
        // The reading the role is created from: its refusal is told on it alone.
        const reading = list?.reading ?? "";
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
            list?.report({ outcome, reading, names: {} });
            return;
          }
          setRefused(problemMessage(own, { locale, messages }));
          input.current?.focus();
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
 * refuse it, with the condition it lacks.
 */
export function DeleteRole({ role }: { readonly role: AccessRole }) {
  const t = useTranslations("admin.accessRoles");
  const told = useTranslations("admin.commands");
  const say = useContext(Say);
  const list = useListReport();
  const [pending, startTransition] = useTransition();
  const described = `${useId()}-unmet`;
  const name = t("deleteRole", { name: role.label });
  const held = role.holder_count > 0 ? t("heldBy", { count: role.holder_count }) : undefined;
  return (
    <>
      <CellCommand
        aria-label={name}
        aria-busy={pending}
        aria-disabled={held === undefined ? undefined : true}
        aria-describedby={held === undefined ? undefined : described}
        title={held}
        className={UNAVAILABLE}
        onClick={() => {
          if (held !== undefined) {
            // An unavailable command never runs: the press says the condition it lacks.
            say?.(told("unmet", { command: name, condition: held }));
            return;
          }
          if (pending) {
            return;
          }
          const reading = list?.reading ?? "";
          startTransition(async () => {
            const outcome = await deleteAccessRole(role.access_role_id).catch(rejected);
            if (outcome.kind === "done") {
              say?.(t("deleted", { name: role.label }));
            } else {
              list?.report({
                outcome,
                reading,
                names: {},
                target: `delete ${role.access_role_id}`,
              });
            }
          });
        }}
      >
        <Trash2 aria-hidden="true" />
        {t("delete")}
      </CellCommand>
      {held === undefined ? null : (
        <span id={described} className="sr-only">
          {held}
        </span>
      )}
    </>
  );
}
