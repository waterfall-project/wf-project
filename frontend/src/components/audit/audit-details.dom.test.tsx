// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { example } from "@/test/fixtures";

import { ActionCell, DetailsCell } from "./audit-cells";
import type { AuditEvent } from "./audit-columns";

type Params = components["schemas"]["AuditParams"];

const events = (example("audit_events") as { items: AuditEvent[] }).items;

/** The inscription of the witness journal of an action, about an object of that label. */
function inscription(action: AuditEvent["action"], label: string): AuditEvent {
  const found = events.find((event) => event.action === action && event.object.label === label);
  if (found === undefined) {
    throw new Error(`the witness journal keeps no ${action} of ${label}`);
  }
  return found;
}

/** The attribution of her role to Camille Martin, which the witness journal keeps. */
const ATTRIBUTION = inscription("user_access_roles_set", "Camille Martin");

/** An inscription of the witness journal, its action and its parameters those of another one. */
function acting(action: AuditEvent["action"], params: Params): AuditEvent {
  return { ...ATTRIBUTION, action, params };
}

/** What a reader of a language reads of an inscription: its action, then what it did. */
function read(event: AuditEvent, locale: Locale): string[] {
  const { container } = render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <p>
        <ActionCell action={event.action} />
      </p>
      <p>
        <DetailsCell event={event} />
      </p>
    </NextIntlClientProvider>,
  );
  return [...container.querySelectorAll("p")].map((part) => part.textContent);
}

describe("what an action did, in the language of its reader", () => {
  it("reads the same attribution of a role in French and in English, the label of the role as it was entered [WF-ARC-0110-A]", () => {
    expect(read(ATTRIBUTION, "fr")).toEqual([
      "Attribution des rôles d’un compte",
      "Rôle donné : Direction de projet",
    ]);
    expect(read(ATTRIBUTION, "en")).toEqual([
      "Roles of an account assigned",
      "Role granted: Direction de projet",
    ]);
  });

  it("names the permissions of a role created by their labels in the catalogue of the reader [WF-ARC-0110-A]", () => {
    const created = inscription("access_role_create", "Auditeur");
    expect(read(created, "fr")[1]).toBe("Permission : Consulter le journal d’audit");
    expect(read(created, "en")[1]).toBe("Permission: View the audit log");
    expect(read(acting("access_role_create", { permissions: [] }), "fr")[1]).toBe(
      "Aucune permission",
    );
  });

  it("names the origin of an account created", () => {
    const created = inscription("user_create", "Dominique Bernard");
    expect(read(created, "fr")[1]).toBe("Importé de l’annuaire");
    expect(read(created, "en")[1]).toBe("Imported from the directory");
  });

  it("names the fields of the identity a modification changed, never their values, and its attachment to the directory", () => {
    const updated = acting("user_update", { fields: ["last_name", "email"], attached: true });
    expect(read(updated, "fr")[1]).toBe(
      "Champs modifiés : Nom et Adresse électronique ; Rattaché à la personne de l’annuaire qui porte son adresse",
    );
    expect(read(updated, "en")[1]).toBe(
      "Fields changed: Last name and Email address; Attached to the person of the directory who holds its address",
    );
  });

  it("names the label a role bore before a modification, and the permissions it granted and withdrew", () => {
    const updated = acting("access_role_update", {
      previous_label: "Contrôle",
      permissions_granted: ["audit_log.read", "users.read"],
      permissions_withdrawn: ["backups.read"],
    });
    expect(read(updated, "fr")[1]).toBe(
      "Auparavant « Contrôle » ; Permissions données : Consulter le journal d’audit et Consulter les utilisateurs ; Permission retirée : Consulter les sauvegardes",
    );
    const unchanged = acting("access_role_update", {
      permissions_granted: [],
      permissions_withdrawn: [],
    });
    expect(read(unchanged, "fr")[1]).toBe("");
  });

  it("names the roles an attribution withdrew, and says when it granted and withdrew none", () => {
    const [role] = ATTRIBUTION.params.access_roles_granted ?? [];
    expect(role).toBeDefined();
    const withdrawn = acting("user_access_roles_set", {
      access_roles_granted: [],
      access_roles_withdrawn: role === undefined ? [] : [role],
    });
    expect(read(withdrawn, "fr")[1]).toBe("Rôle retiré : Direction de projet");
    expect(read(withdrawn, "en")[1]).toBe("Role withdrawn: Direction de projet");
    const same = acting("user_access_roles_set", {
      access_roles_granted: [],
      access_roles_withdrawn: [],
    });
    expect(read(same, "en")[1]).toBe("No role granted nor withdrawn");
  });

  it("says nothing more of an action whose object says it all", () => {
    expect(read(inscription("user_deactivate", "Alix Moreau"), "fr")).toEqual([
      "Désactivation d’un compte",
      "",
    ]);
  });
});
