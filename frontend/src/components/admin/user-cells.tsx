// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the table of the accounts that write it (US-0360, #379), for a session that may modify
 * the accounts, each as the account lists its command (`available_commands`):
 *
 * - the state, on a switch, with its word beside it — deactivated or reactivated from the version the
 *   screen holds (`setUserActivation`), never deleted (WF-ADM-0060); the deactivation of the last
 *   administrator is unavailable, as the account lists it (WF-ADM-0120): marked `aria-disabled`,
 *   described by the condition it lacks, and, pressed, saying it in the region of the table;
 * - the access roles, a list of several choices of the roles of the installation, whatever the node
 *   the account is attached to (WF-ADM-0030): each role checked or unchecked writes the roles of the
 *   account (`setUserAccessRoles`), none, one or more (WF-ADM-0050) — the server judges the roles
 *   sent, and refuses by `LAST_ADMINISTRATOR` those that would take its permissions from the last
 *   administrator (WF-ADM-0120);
 * - the link by which the holder of a local account sets its password (`createPasswordSetupLink`),
 *   offered to a local account alone — another sets none in Waterfall, an anonymised one is withdrawn
 *   from the identity provider —, unavailable while it is deactivated, as the server would refuse it
 *   (`is_active_account`);
 * - the anonymisation, offered to a deactivated account only and unavailable once it is anonymised,
 *   its reactivation unavailable too (WF-ADM-0060): confirmed first, being irreversible
 *   (`AnonymizeCommand`).
 *
 * While a write of its row is under way, whatever its cell, each is marked busy, and the switch, the
 * roles and the anonymisation unavailable: a press asks nothing (`UserWrites.busy`).
 *
 * In a dense grid, each is out of the order of tabulation, the grid being one stop: Enter on its cell
 * presses it (`CELL_COMMAND`). Every prop is data, never a function (défaut n° 12 de `typescript.md`).
 */
"use client";

import { ChevronDown, KeyRound, UserRoundX } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useRef } from "react";

import { setUserAccessRoles, setUserActivation } from "@/api/actions/users";
import { useAccountNaming } from "@/components/account/account-name";
import { useUnmet } from "@/components/commands/command";
import { type CommandOffer, findOffer, UNAVAILABLE } from "@/components/commands/offer";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
import { CellCommand } from "@/components/reference/cell-command";
import { useListReport } from "@/components/reference/reactivation";
import { ActiveState } from "@/components/reference/section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";

import type { RoleChoice, User } from "./admin-grids";
import { useUserWrites } from "./user-commands";

/** The roles of an account, as the server names them, or that it holds none. */
export function HeldRoles({ labels }: { readonly labels: readonly string[] }) {
  const t = useTranslations("admin.users");
  return labels.length === 0 ? (
    <span className="text-muted-foreground">{t("noRole")}</span>
  ) : (
    <span className="flex gap-1">
      {labels.map((label, at) => (
        <Badge key={`${String(at)} ${label}`} variant="secondary">
          {label}
        </Badge>
      ))}
    </span>
  );
}

/**
 * The state of an account, its word beside the switch that changes it as the account lists it; the
 * word alone when it lists no command of its state.
 */
export function StateSwitch({ user }: { readonly user: User }) {
  const t = useTranslations("admin.users");
  const writes = useUserWrites();
  const list = useListReport();
  const unmet = useUnmet();
  const naming = useAccountNaming();
  const name = naming.person(user);
  const control = useRef<HTMLButtonElement>(null);
  const described = `${useId()}-unmet`;
  const command = user.is_active ? "deactivate" : "reactivate";
  const offer = findOffer(user.available_commands, command);
  const asked = writes?.asked.get(user.user_id);
  const busy = writes?.busy.has(user.user_id) === true;
  const active = asked?.is_active ?? user.is_active;
  if (offer === undefined || writes === undefined) {
    return <ActiveState active={user.is_active} />;
  }
  const lacking = offer.is_available ? undefined : unmet(offer);
  return (
    <span className="inline-flex items-center gap-1.5">
      <Switch
        ref={control}
        checked={active}
        tabIndex={-1}
        {...{ [CELL_COMMAND]: "" }}
        aria-label={t("activeUser", { name })}
        aria-busy={busy}
        aria-disabled={lacking === undefined && !busy ? undefined : true}
        aria-describedby={lacking === undefined ? undefined : described}
        title={lacking}
        className={UNAVAILABLE}
        onCheckedChange={(checked) => {
          if (lacking !== undefined) {
            // An unavailable command never runs: the press says the condition it lacks.
            list?.tell(name, offer, command);
            return;
          }
          if (busy) {
            // Marked busy and unavailable: the write of the row under way is answered first.
            return;
          }
          writes.run(user, {
            target: `activation ${user.user_id}`,
            asked: { is_active: checked },
            send: (shown) =>
              setUserActivation(shown.user_id, {
                is_active: checked,
                lock_version: shown.lock_version,
              }),
            said: (answered) =>
              t(answered.is_active ? "reactivated" : "deactivated", {
                name: naming.person(answered),
              }),
            back: control.current,
          });
        }}
      />
      <ActiveState active={active} />
      {lacking === undefined ? null : (
        <span id={described} className="sr-only">
          {lacking}
        </span>
      )}
    </span>
  );
}

/**
 * The access roles of an account, and the list of the roles of the installation that attributes them,
 * each checked when the account holds it — the roles asked shown until the server answers; the roles
 * alone when the account lists no attribution, or the session reads no role.
 */
export function RolesCell({
  user,
  roles,
}: {
  readonly user: User;
  /** The roles of the installation, in the order the server gives them. */
  readonly roles: readonly RoleChoice[];
}) {
  const t = useTranslations("admin.users");
  const writes = useUserWrites();
  const naming = useAccountNaming();
  const name = naming.person(user);
  const trigger = useRef<HTMLButtonElement>(null);
  const group = useId();
  const offer = findOffer(user.available_commands, "set_access_roles");
  const asked = writes?.asked.get(user.user_id)?.access_role_ids;
  const busy = writes?.busy.has(user.user_id) === true;
  if (offer === undefined || writes === undefined || roles.length === 0) {
    return <HeldRoles labels={user.access_role_labels} />;
  }
  const held = asked ?? user.access_role_ids;
  // The labels of the roles asked, as the server named them in the list of the roles.
  const labels =
    asked === undefined
      ? user.access_role_labels
      : asked.map((id) => roles.find((role) => role.id === id)?.label ?? id);
  const toggle = (role: string, checked: boolean) => {
    if (busy) {
      // Marked busy and unavailable: the write of the row under way is answered first.
      return;
    }
    const current = writes.latest(user).access_role_ids;
    const next = checked
      ? [...current.filter((each) => each !== role), role]
      : current.filter((each) => each !== role);
    writes.run(user, {
      target: `roles ${user.user_id}`,
      asked: { access_role_ids: next },
      send: (shown) =>
        setUserAccessRoles(shown.user_id, {
          access_role_ids: next,
          lock_version: shown.lock_version,
        }),
      said: (answered) =>
        t("rolesAttributed", {
          name: naming.person(answered),
        }),
      back: trigger.current,
    });
  };
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          ref={trigger}
          type="button"
          variant="ghost"
          size="sm"
          tabIndex={-1}
          {...{ [CELL_COMMAND]: "" }}
          aria-label={t("rolesOf", { name })}
          aria-busy={busy}
          className="h-5 max-w-full justify-start px-0.5 font-normal"
        >
          <HeldRoles labels={labels} />
          <ChevronDown aria-hidden="true" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        aria-labelledby={group}
        className="w-64"
        onCloseAutoFocus={(event) => {
          // The grid is one stop: the focus goes back to the cell, never to its command.
          event.preventDefault();
          (trigger.current?.closest<HTMLElement>("td") ?? trigger.current)?.focus();
        }}
      >
        <div role="group" aria-labelledby={group} className="grid gap-2">
          <p id={group} className="text-sm font-medium">
            {t("rolesOf", { name })}
          </p>
          {roles.map((role) => {
            const box = `${group}-${role.id}`;
            return (
              <div key={role.id} className="flex items-center gap-2">
                <Checkbox
                  id={box}
                  checked={held.includes(role.id)}
                  aria-disabled={busy ? true : undefined}
                  className="aria-disabled:opacity-50"
                  onCheckedChange={(checked) => {
                    toggle(role.id, checked === true);
                  }}
                />
                <Label htmlFor={box} className="font-normal">
                  {role.label}
                </Label>
              </div>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}

/** A link asked of a deactivated account: the server would refuse it (`is_active_account`). */
const DEACTIVATED: CommandOffer = {
  is_available: false,
  missing_conditions: ["is_active_account"],
};

/**
 * The command that asks the link of a local account, named after it — unavailable while the account
 * is deactivated, as the server would refuse it —; none for another account, which sets no password
 * in Waterfall, nor for an anonymised one, withdrawn from the identity provider (WF-ADM-0060).
 */
export function SetupLinkCommand({ user }: { readonly user: User }) {
  const t = useTranslations("admin.users");
  const told = useTranslations("admin.commands");
  const writes = useUserWrites();
  const unmet = useUnmet();
  const name = useAccountNaming().person(user);
  const described = `${useId()}-unmet`;
  if (user.origin !== "local" || user.anonymized_at !== null || writes === undefined) {
    return null;
  }
  const command = t("linkOf", { name });
  const lacking = user.is_active ? undefined : unmet(DEACTIVATED);
  const pending = writes.linking.has(user.user_id);
  return (
    <>
      <CellCommand
        aria-label={command}
        aria-busy={pending}
        aria-disabled={lacking === undefined ? undefined : true}
        aria-describedby={lacking === undefined ? undefined : described}
        title={lacking}
        className={UNAVAILABLE}
        onClick={(event) => {
          if (lacking !== undefined) {
            // An unavailable command never runs: the press says the condition it lacks.
            writes.say(told("unmet", { command, condition: lacking }));
            return;
          }
          if (!pending) {
            writes.giveLink(user, name, event.currentTarget);
          }
        }}
      >
        <KeyRound aria-hidden="true" />
        {t("link")}
      </CellCommand>
      {lacking === undefined ? null : (
        <span id={described} className="sr-only">
          {lacking}
        </span>
      )}
    </>
  );
}

/**
 * The anonymisation of an account, as the account lists it: offered to a deactivated account only,
 * unavailable once it is anonymised — marked `aria-disabled`, described by the condition it lacks
 * (WF-ADM-0060) —, and nothing when the account does not list it. Pressed, it asks the confirmation
 * of the table, which says the anonymisation irreversible (`UserWrites.anonymize`); unavailable, it
 * says the condition it lacks. Like the switch, it is marked busy while a write of its row is under
 * way, and unavailable the while, or while a reactivation asked is unanswered: a press asks nothing.
 */
export function AnonymizeCommand({ user }: { readonly user: User }) {
  const t = useTranslations("admin.users");
  const told = useTranslations("admin.commands");
  const writes = useUserWrites();
  const unmet = useUnmet();
  const naming = useAccountNaming();
  const control = useRef<HTMLButtonElement>(null);
  const described = `${useId()}-unmet`;
  const offer = findOffer(user.available_commands, "anonymize");
  if (offer === undefined || writes === undefined) {
    return null;
  }
  const busy = writes.busy.has(user.user_id);
  const held = busy || writes.asked.get(user.user_id)?.is_active === true;
  const named = t("anonymizeUser", { name: naming.person(user) });
  const lacking = offer.is_available ? undefined : unmet(offer);
  return (
    <>
      <CellCommand
        ref={control}
        aria-label={named}
        aria-busy={busy}
        aria-disabled={lacking === undefined && !held ? undefined : true}
        aria-describedby={lacking === undefined ? undefined : described}
        title={lacking}
        className={UNAVAILABLE}
        onClick={() => {
          if (lacking !== undefined) {
            // An unavailable command never runs: the press says the condition it lacks.
            writes.say(told("unmet", { command: named, condition: lacking }));
            return;
          }
          if (!held) {
            writes.anonymize(user, control.current);
          }
        }}
      >
        <UserRoundX aria-hidden="true" />
        {t("anonymize")}
      </CellCommand>
      {lacking === undefined ? null : (
        <span id={described} className="sr-only">
          {lacking}
        </span>
      )}
    </>
  );
}
