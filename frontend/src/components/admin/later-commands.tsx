// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the accounts and of the access roles (FBS-1.1, FBS-1.2, #379, #515), placed
 * before EP-03 wires them (US-0360/L3, US-0380/L2): create a local account, modify one, deactivate
 * or reactivate it, attribute its roles — no account is deleted (WF-ADM-0060) —; create a role,
 * modify one, delete one — a logical deletion, decided by the framing of EP-03 (#456): the role is
 * no longer read nor attributable. They are offered only to a session that may modify the function
 * — `users.write`, `access_roles.write` (`platformOffer`) —, and none to another: the screen
 * presents only what the user may do (WF-IHM-0090). Pressed, a command says it is available with
 * EP-03, in one region announced — each press, the same one pressed again too —; nothing is asked
 * of the server.
 *
 * A command the server declares it would refuse is presented unavailable, as `Command` does: a
 * role an account holds is not deleted (`deleteAccessRole`, 409, WF-ADM-0090) — its deletion is
 * marked `aria-disabled`, described by the condition it lacks; a press does not run it, and says in
 * the region the condition it lacks.
 *
 * Every prop is data — the command, the name of the object —, never a function: a server component
 * hands them over (défaut n° 12 de `typescript.md`). In a dense grid, a command is out of the order
 * of tabulation, the grid being one stop: Enter on its cell presses it (`CELL_COMMAND`).
 */
"use client";

import {
  KeyRound,
  type LucideIcon,
  PencilLine,
  Plus,
  RotateCcw,
  Trash2,
  UserPlus,
  UserX,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { createContext, type ReactNode, useContext, useId, useMemo, useState } from "react";

import { UNAVAILABLE } from "@/components/commands/offer";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
import { Button } from "@/components/ui/button";
import { cn } from "@/components/ui/utils";

/**
 * What the last command pressed says — that it is available later, or the condition it lacks when
 * it is unavailable —, and the how-many-th press it was.
 */
interface Told {
  readonly command: string;
  readonly unmet: string | undefined;
  readonly press: number;
}

/** How a command pressed says what it does; none outside the commands of a screen. */
const Announce = createContext<((command: string, unmet: string | undefined) => void) | undefined>(
  undefined,
);

/** What the last command pressed says; none before any press. */
const Said = createContext<Told | undefined>(undefined);

/** The commands of a screen, which share the region that says what the last one pressed does. */
export function LaterCommands({ children }: { readonly children: ReactNode }) {
  const [told, setTold] = useState<Told>();
  const announce = useMemo(
    () => (command: string, unmet: string | undefined) => {
      setTold((before) => ({ command, unmet, press: (before?.press ?? 0) + 1 }));
    },
    [],
  );
  return (
    <Announce value={announce}>
      <Said value={told}>{children}</Said>
    </Announce>
  );
}

/**
 * The region that says what the last command pressed does — available with EP-03, or the condition
 * it lacks —, rendered from the start, so that a reader of the screen hears what is put in it; each
 * press puts a new text in it, the same command pressed again too.
 */
export function LaterNotice() {
  const t = useTranslations("admin.commands");
  const told = useContext(Said);
  return (
    <p role="status" aria-live="polite" className="min-h-5 text-sm text-muted-foreground">
      {told === undefined ? null : (
        <span key={told.press}>
          {told.unmet === undefined
            ? t("later", { command: told.command })
            : t("unmet", { command: told.command, condition: told.unmet })}
        </span>
      )}
    </p>
  );
}

/** A command that says it is available later, or unavailable with the condition it lacks. */
function LaterButton({
  icon: Icon,
  text,
  named,
  cell,
  unavailable,
}: {
  readonly icon: LucideIcon;
  /** What the button shows. */
  readonly text: string;
  /** Its accessible name, which names the object; the text when none. */
  readonly named?: string;
  /** Whether it is the command of a cell of a dense grid. */
  readonly cell: boolean;
  /** The condition it lacks, when it is unavailable. */
  readonly unavailable?: string | undefined;
}) {
  const announce = useContext(Announce);
  const id = useId();
  const described = unavailable === undefined ? undefined : `${id}-unmet`;
  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        {...(cell ? { tabIndex: -1, [CELL_COMMAND]: "" } : {})}
        aria-label={named}
        aria-disabled={unavailable === undefined ? undefined : true}
        aria-describedby={described}
        title={unavailable}
        className={cn(cell ? "h-5 px-1.5 text-xs" : "self-start", UNAVAILABLE)}
        onClick={() => {
          // An unavailable command never runs: the press says the condition it lacks.
          announce?.(named ?? text, unavailable);
        }}
      >
        <Icon aria-hidden="true" />
        {text}
      </Button>
      {described === undefined ? null : (
        <span id={described} className="sr-only">
          {unavailable}
        </span>
      )}
    </>
  );
}

/** The command that creates a role, or a local account. */
export function CreateCommand({ kind }: { readonly kind: "role" | "localAccount" }) {
  const t = useTranslations("admin");
  return kind === "role" ? (
    <LaterButton icon={Plus} text={t("accessRoles.create")} cell={false} />
  ) : (
    <LaterButton icon={UserPlus} text={t("users.create")} cell={false} />
  );
}

/** A command of a role. */
export type RoleCommandName = "modify" | "delete";

/**
 * A command of a role, named after it; its deletion unavailable while an account holds it, as the
 * server would refuse it.
 */
export function RoleCommand({
  command,
  name,
  holders,
}: {
  readonly command: RoleCommandName;
  /** The label of the role, as the list shows it. */
  readonly name: string;
  /** How many accounts hold the role, as the server counts them. */
  readonly holders: number;
}) {
  const t = useTranslations("admin.accessRoles");
  return command === "modify" ? (
    <LaterButton icon={PencilLine} text={t("modify")} named={t("modifyRole", { name })} cell />
  ) : (
    <LaterButton
      icon={Trash2}
      text={t("delete")}
      named={t("deleteRole", { name })}
      cell
      unavailable={holders > 0 ? t("heldBy", { count: holders }) : undefined}
    />
  );
}

/** A command of an account: none deletes it (WF-ADM-0060). */
export type UserCommandName = "modify" | "activation" | "assignRoles";

/**
 * A command of an account, named after it: its modification, its deactivation or its reactivation
 * as it is active or not, the attribution of its roles.
 */
export function UserCommand({
  command,
  name,
  active,
}: {
  readonly command: UserCommandName;
  /** The name of the account, as the list shows it. */
  readonly name: string;
  readonly active: boolean;
}) {
  const t = useTranslations("admin.users");
  switch (command) {
    case "modify":
      return (
        <LaterButton icon={PencilLine} text={t("modify")} named={t("modifyUser", { name })} cell />
      );
    case "activation":
      return active ? (
        <LaterButton
          icon={UserX}
          text={t("deactivate")}
          named={t("deactivateUser", { name })}
          cell
        />
      ) : (
        <LaterButton
          icon={RotateCcw}
          text={t("reactivate")}
          named={t("reactivateUser", { name })}
          cell
        />
      );
    case "assignRoles":
      return (
        <LaterButton
          icon={KeyRound}
          text={t("assignRoles")}
          named={t("assignRolesUser", { name })}
          cell
        />
      );
  }
}
