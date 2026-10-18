// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The table of the accounts of the witness, for the unit tests of its commands: the accounts the
 * examples of the contract hold, rendered in French as the page of the administration renders
 * them, and the gestures and readings those tests share. The server of Next — the fake back, the
 * address, the navigations — is each test file's own: `vi.mock` is hoisted in the file it is
 * written in.
 */
import { screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { UserList } from "@/components/admin/account-lists";
import type { AccessRole, User } from "@/components/admin/admin-grids";
import { readAuditFilters } from "@/components/admin/audit-address";
import { USER_KEPT } from "@/components/admin/user-address";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";

import { example, type FakeClient, type FakeTiming } from "./fixtures";

type Schemas = components["schemas"];

/** The accounts of the witness, as the first page of their list holds them. */
export const users = example("users") as { items: User[]; meta: Schemas["PaginationMeta"] };

/** The access roles of the installation, as the table names them. */
export const roles = (example("access_roles") as AccessRole[]).map((role) => ({
  id: role.access_role_id,
  label: role.label,
}));

/** No filter of the audit columns. */
export const NO_AUDIT = readAuditFilters(new URLSearchParams());

/** The calls the screen made, but the settings of its grid. */
export function writes(client: FakeClient) {
  return client.calls
    .filter(({ route }) => route !== "PATCH /me/preferences")
    .map(({ route, path, body }) => [route, path, body]);
}

/** The accounts of the witness, in French, as a session that may modify them, or not, reads them. */
export function accounts(
  editable = true,
  shown: readonly User[] = users.items,
  kept?: GridPreferences,
): ReactNode {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={USER_KEPT}>
        <UserList
          users={shown}
          page={users.meta}
          query={{ sort: undefined, search: undefined }}
          preferences={kept}
          origins={[]}
          nodes={[]}
          orgNode={undefined}
          roles={roles}
          accessRoles={[]}
          active={undefined}
          audit={NO_AUDIT}
          authors={[]}
          editable={editable}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The grid of the accounts. */
export function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Comptes utilisateurs" });
}

/** The region of the table that says what its last command did, by its name. */
export function told(): HTMLElement {
  return screen.getByRole("status", { name: "Commandes des comptes" });
}

/** Hold the answers of a route until released: a write under way. */
export function holdRoute(held: string): {
  readonly timing: FakeTiming;
  readonly release: () => void;
} {
  const settles: (() => void)[] = [];
  const until = new Promise<void>((settle) => {
    settles.push(settle);
  });
  return {
    timing: {
      hold: (route) => (route === held ? until : undefined),
    },
    release: () => {
      for (const settle of settles) {
        settle();
      }
    },
  };
}

/** Hold the deactivations until released: a write of a row under way. */
export function heldActivation() {
  return holdRoute("PUT /users/{user_id}/activation");
}

/** Open the creation of a local account, and give its form. */
export async function openCreation(): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole("button", { name: "Créer un compte local" }));
  return screen.findByRole("form", { name: "Créer un compte local" });
}

/** Fill the creation of Léa Garnier, and send it. */
export async function createGarnier(form: HTMLElement) {
  await userEvent.type(within(form).getByLabelText("Nom"), "Garnier");
  await userEvent.type(within(form).getByLabelText("Prénom"), "Léa");
  await userEvent.type(within(form).getByLabelText("Adresse électronique"), "l@example.com");
  await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
}

/** An account of the witness, by its last name. */
export function account(lastName: string): User {
  const found = users.items.find((user) => user.last_name === lastName);
  if (found === undefined) {
    throw new Error(`no account ${lastName} in the witness`);
  }
  return found;
}
