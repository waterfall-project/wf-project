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
 *   administrator (WF-ADM-0120).
 *
 * In a dense grid, each is out of the order of tabulation, the grid being one stop: Enter on its cell
 * presses it (`CELL_COMMAND`). Every prop is data, never a function (défaut n° 12 de `typescript.md`).
 */
"use client";

import { ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useRef } from "react";

import { setUserAccessRoles, setUserActivation } from "@/api/actions/users";
import { useUnmet } from "@/components/commands/command";
import { findOffer, UNAVAILABLE } from "@/components/commands/offer";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
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

/** The name of an account, as the table shows it. */
function useNamed(): (user: User) => string {
  const t = useTranslations("admin.users");
  return (user) => t("named", { firstName: user.first_name, lastName: user.last_name });
}

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
  const name = useNamed()(user);
  const control = useRef<HTMLButtonElement>(null);
  const described = `${useId()}-unmet`;
  const command = user.is_active ? "deactivate" : "reactivate";
  const offer = findOffer(user.available_commands, command);
  const asked = writes?.asked.get(user.user_id);
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
        aria-busy={asked !== undefined}
        aria-disabled={lacking === undefined && asked === undefined ? undefined : true}
        aria-describedby={lacking === undefined ? undefined : described}
        title={lacking}
        className={UNAVAILABLE}
        onCheckedChange={(checked) => {
          if (lacking !== undefined) {
            // An unavailable command never runs: the press says the condition it lacks.
            list?.tell(name, offer, command);
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
                name: t("named", { firstName: answered.first_name, lastName: answered.last_name }),
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
  const name = useNamed()(user);
  const trigger = useRef<HTMLButtonElement>(null);
  const group = useId();
  const offer = findOffer(user.available_commands, "set_access_roles");
  const asked = writes?.asked.get(user.user_id)?.access_role_ids;
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
    if (asked !== undefined) {
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
          name: t("named", { firstName: answered.first_name, lastName: answered.last_name }),
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
          aria-busy={asked !== undefined}
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
                  aria-disabled={asked === undefined ? undefined : true}
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
