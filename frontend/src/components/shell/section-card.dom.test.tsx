// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of a section (US-2070): a section named after its title, its commands at the right of
 * the title, its body; and the rule of the commands it carries, which `expectCommandRule` reads —
 * one filled command at most in a card, its principal one when it creates or triggers, outlined
 * when it modifies; none filled at the right of the title of a screen.
 */
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { Plus } from "lucide-react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";
import { expectAccessible } from "@/test/axe";
import { commandRuleBreaches, expectCommandRule } from "@/test/command-rule";

import { PageHeader } from "./page-header";
import { type PrincipalDoes, principalVariant, SectionCard } from "./section-card";

/** A card of the natures of cost: a command of its own, its principal one, a field in its body. */
function natures(does: PrincipalDoes) {
  return (
    <SectionCard
      title="Natures de coût"
      icon={Plus}
      description="Les natures que portent les catégories."
      commands={<Button variant="outline">Exporter</Button>}
      principal={{
        does,
        command: <Button variant={principalVariant(does)}>Nouvelle nature</Button>,
      }}
    >
      <label>
        Rechercher
        <input type="search" />
      </label>
    </SectionCard>
  );
}

describe("the card of a section", () => {
  it("is a section named after its title, a heading under the title of the screen, and breaks no rule of accessibility", async () => {
    const { container } = render(natures("create"));
    const card = screen.getByRole("region", { name: "Natures de coût" });
    expect(within(card).getByRole("heading", { level: 2 }).textContent).toBe("Natures de coût");
    expect(within(card).getByText("Les natures que portent les catégories.")).toBeInTheDocument();
    await expectAccessible(container);
  });

  it("sets its commands at the right of its title, the principal one last, and its body under them", () => {
    render(natures("create"));
    const card = screen.getByRole("region", { name: "Natures de coût" });
    const order = [
      within(card).getByRole("heading", { level: 2 }),
      within(card).getByRole("button", { name: "Exporter" }),
      within(card).getByRole("button", { name: "Nouvelle nature" }),
      within(card).getByRole("searchbox", { name: "Rechercher" }),
    ];
    const shown = [...card.querySelectorAll("h2, button, input")];
    expect(shown).toEqual(order);
    // The commands stand together, beside the title rather than under it: one block of the header.
    const commands = within(card).getByRole("button", { name: "Exporter" }).parentElement;
    expect(commands?.contains(screen.getByRole("button", { name: "Nouvelle nature" }))).toBe(true);
    expect(commands?.contains(within(card).getByRole("heading", { level: 2 }))).toBe(false);
  });

  it("is walked by Tab from its commands to its body, in the order it shows them [WF-IHM-0100-A]", async () => {
    render(natures("create"));
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Exporter" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Nouvelle nature" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("searchbox", { name: "Rechercher" })).toHaveFocus();
  });

  it("renders no block of commands when it has none", () => {
    render(
      <SectionCard title="Seuils">
        <p>Aucun seuil.</p>
      </SectionCard>,
    );
    const card = screen.getByRole("region", { name: "Seuils" });
    expect(card.querySelector('[data-slot="section-card-commands"]')).toBeNull();
    expect(within(card).queryAllByRole("button")).toEqual([]);
  });
});

describe("the rule of the commands", () => {
  it.each([
    ["create", "default"],
    ["trigger", "default"],
    ["modify", "outline"],
  ] as const)(
    "fills the principal command of a card that does %s as %s, and the card keeps the rule",
    (does, variant) => {
      expect(principalVariant(does)).toBe(variant);
      const { container } = render(natures(does));
      expectCommandRule(container);
    },
  );

  it("names a second filled command in a card", () => {
    const { container } = render(
      <SectionCard
        title="Natures de coût"
        commands={<Button>Importer</Button>}
        principal={{ does: "create", command: <Button>Nouvelle nature</Button> }}
      >
        <Button>Enregistrer</Button>
      </SectionCard>,
    );
    expect(commandRuleBreaches(container)).toEqual([
      "the card « Natures de coût » offers « Importer » filled",
      "the card « Natures de coût » offers « Enregistrer » filled",
    ]);
  });

  it("names a principal command filled that modifies, and one outlined that creates", () => {
    const { container } = render(
      <>
        <SectionCard
          title="Paramètres"
          principal={{ does: "modify", command: <Button>Modifier</Button> }}
        >
          <p>Devise : EUR</p>
        </SectionCard>
        <SectionCard
          title="Catégories"
          principal={{ does: "create", command: <Button variant="outline">Créer</Button> }}
        >
          <p>Aucune catégorie.</p>
        </SectionCard>
      </>,
    );
    expect(commandRuleBreaches(container)).toEqual([
      "the card « Paramètres » fills a principal command that modifies",
      "the card « Catégories » has 0 filled principal commands, not one",
    ]);
  });

  it("names a command of a screen filled at the right of its title, and lets an outlined one pass", () => {
    const { container } = render(
      <PageHeader
        title="Paramètres de coûts"
        helped={false}
        actions={
          <>
            <Button variant="outline">Correspondance</Button>
            <Button>Nouvelle nature</Button>
          </>
        }
      />,
    );
    expect(commandRuleBreaches(container)).toEqual([
      "the screen offers « Nouvelle nature » filled",
    ]);
  });
});
