// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { cleanup, render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { example } from "@/test/fixtures";

import { ActionCell } from "./audit-cells";
import type { AuditEvent } from "./audit-columns";

/**
 * The inscriptions of the witness journals: that of the installation, and that of the administration
 * of the accounts and of the roles, each written as the service inscribes it.
 */
const events = ["audit_events", "audit_events_administration"].flatMap(
  (name) => (example(name) as { items: AuditEvent[] }).items,
);

/** The inscription of a witness journal of an action, about an object of that label. */
function inscription(action: AuditEvent["action"], label: string): AuditEvent {
  const found = events.filter((event) => event.action === action && event.object.label === label);
  if (found.length !== 1 || found[0] === undefined) {
    throw new Error(`the witness journals keep no single ${action} of ${label}`);
  }
  return found[0];
}

/** The second line of the cell of the action of an inscription, once rendered. */
function detailsOf(event: AuditEvent, locale: Locale): Element | undefined {
  const { container } = render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <p>
        <ActionCell event={event} />
      </p>
    </NextIntlClientProvider>,
  );
  return [...container.querySelectorAll("p > span > span")].at(1);
}

/**
 * What a reader of a language reads in the cell of the action of an inscription: the action, then
 * under it what it did, or the action alone.
 */
function read(event: AuditEvent, locale: Locale): string[] {
  const { container } = render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <p>
        <ActionCell event={event} />
      </p>
    </NextIntlClientProvider>,
  );
  const lines = [...container.querySelectorAll("p > span > span")];
  return lines.length === 0 ? [container.textContent] : lines.map((line) => line.textContent);
}

describe("what an action did, under the action, in the language of its reader", () => {
  it("reads the same attribution of a role in French and in English, the label of the role as it was entered [WF-ARC-0110-A]", () => {
    const attribution = inscription("user_access_roles_set", "Lucas Petit");
    expect(read(attribution, "fr")).toEqual([
      "Attribution des rôles d’un compte",
      "Rôle donné : Chiffreur",
    ]);
    expect(read(attribution, "en")).toEqual([
      "Roles of an account assigned",
      "Role granted: Chiffreur",
    ]);
  });

  it("names the permissions of a role created by their labels in the catalogue of the reader, or that it has none [WF-ARC-0110-A]", () => {
    const created = inscription("access_role_create", "Auditeur");
    expect(read(created, "fr")[1]).toBe("Permission : Consulter le journal d’audit");
    expect(read(created, "en")[1]).toBe("Permission: View the audit log");
    const bare = inscription("access_role_create", "Contrôle de gestion");
    expect(read(bare, "fr")).toEqual(["Création d’un rôle", "Aucune permission"]);
    expect(read(bare, "en")[1]).toBe("No permission");
  });

  it("names the origin of an account created, and the first roles an attribution of its own gave it after", () => {
    expect(read(inscription("user_create", "Dominique Bernard"), "fr")[1]).toBe(
      "Importé de l’annuaire",
    );
    const created = inscription("user_create", "Léa Garnier");
    expect(read(created, "fr")[1]).toBe("Créé dans Waterfall");
    expect(read(created, "en")[1]).toBe("Created in Waterfall");
    // An account is born with no role, and its roles are attributed under a request of their own (A-01).
    const given = inscription("user_access_roles_set", "Léa Garnier");
    expect(given.correlation_id).not.toBe(created.correlation_id);
    expect(read(given, "fr")[1]).toBe("Rôle donné : Chiffreur");
  });

  it("names the fields of the identity a modification changed, never their values, and its attachment to the directory", () => {
    const renamed = inscription("user_update", "Lucas Petit-Laurent");
    expect(read(renamed, "fr")).toEqual(["Modification d’un compte", "Champ modifié : Nom"]);
    const attached = inscription("user_update", "Noé Vidal-Roux");
    expect(read(attached, "fr")[1]).toBe(
      "Champ modifié : Nom ; Origine désormais : Importé de l’annuaire",
    );
    expect(read(attached, "en")[1]).toBe(
      "Field changed: Last name; Origin from now on: Imported from the directory",
    );
  });

  it("names the label a role bore before a modification, and the permissions it granted and withdrew", () => {
    const updated = inscription("access_role_update", "Responsable d'équipe");
    expect(read(updated, "fr")[1]).toBe(
      "Auparavant « Manager » ; Permission donnée : Modifier la planification ; Permissions retirées : Modifier les paramètres de coûts et Modifier les paramètres de ressources",
    );
    expect(read(updated, "en")[1]).toBe(
      "Formerly “Manager”; Permission granted: Edit planning; Permissions withdrawn: Edit cost settings and Edit resource settings",
    );
  });

  it("names the roles an attribution withdrew, by the labels they bore then", () => {
    const withdrawn = inscription("user_access_roles_set", "Inès Roux");
    expect(read(withdrawn, "fr")[1]).toBe("Rôle retiré : Pilotage de projet");
    expect(read(withdrawn, "en")[1]).toBe("Role withdrawn: Pilotage de projet");
  });

  it.each([
    ["a deactivation", "user_deactivate", "Alix Moreau", "Désactivation d’un compte"],
  ] as const)("says nothing more of %s than its action", (_, action, label, said) => {
    expect(read(inscription(action, label), "fr")).toEqual([said]);
  });

  it("says in a sentence that a modification of a role changed neither its label nor its permissions [WF-ARC-0110-A]", () => {
    const unchanged = inscription("access_role_update", "Contrôle de gestion");
    expect(read(unchanged, "fr")).toEqual([
      "Modification d’un rôle",
      "Ni le libellé ni les permissions n’ont changé",
    ]);
    expect(read(unchanged, "en")[1]).toBe("Neither the label nor the permissions changed");
  });
});

/** Make the elements measure as cut short by their width, or not. */
function measureCut(cut: boolean): void {
  vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(cut ? 200 : 100);
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(100);
}

describe("the title of the cell of the action", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  const restored = (params: AuditEvent["params"]): AuditEvent => ({
    ...inscription("user_access_roles_set", "Lucas Petit"),
    action: "restore",
    params,
  });

  it("is posed only when the cell cuts its text short, so that no technology reads it twice", () => {
    measureCut(false);
    expect(
      detailsOf(inscription("access_role_update", "Responsable d'équipe"), "fr")?.getAttribute(
        "title",
      ),
    ).toBeNull();
    cleanup();
    measureCut(true);
    expect(
      detailsOf(inscription("access_role_update", "Responsable d'équipe"), "fr")?.getAttribute(
        "title",
      ),
    ).toMatch(/^Auparavant « Manager » ; Permission donnée/);
  });

  it("gives, once cut, the instant of the backup restored alone and after the reason [WF-ADM-0160-A]", () => {
    measureCut(true);
    const instant = "2026-06-01T10:00:00Z";
    const alone = detailsOf(restored({ backup_taken_at: instant }), "fr");
    expect(alone?.getAttribute("title")).toBe(alone?.textContent);
    expect(alone?.getAttribute("title")).toMatch(/^Sauvegarde restaurée du .*2026/);
    cleanup();
    const explained = detailsOf(restored({ backup_taken_at: instant, reason: "Incident" }), "fr");
    expect(explained?.getAttribute("title")).toBe(explained?.textContent);
    expect(explained?.getAttribute("title")).toMatch(
      /^Motif : Incident ; Sauvegarde restaurée du .*2026/,
    );
  });

  it("is not posed on a restoration shown whole", () => {
    measureCut(false);
    const alone = detailsOf(restored({ backup_taken_at: "2026-06-01T10:00:00Z" }), "fr");
    expect(alone?.hasAttribute("title")).toBe(false);
  });
});
