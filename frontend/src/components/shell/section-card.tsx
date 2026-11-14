// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of a section of a screen (EP-25, « Une carte de section commune »), beside the header of
 * the screen: its title, its commands at the right of the title, its body. A section of a screen is
 * a card, named after its title, which a screen never composes itself — it would decide the rule of
 * the commands anew, screen by screen.
 *
 * The rule of the commands (#3088, rules 2 to 4; #3090): a card has one principal command at most,
 * the last at the right of its title, filled when it creates or triggers, outlined when it modifies;
 * its other commands are outlined, as are those of the screen at the right of its title. The filled
 * button is for the principal command alone: a current choice says itself otherwise. The card says
 * what its principal command does (`principal.does`), the command takes its variant from the same
 * word (`principalVariant`), and `expectCommandRule` (`src/test/command-rule.ts`) holds the two
 * together in the tests of a screen. The commands wrap under the title rather than overflow the
 * card: at a zoom of 150 %, none goes out of reach (WF-IHM-0100).
 *
 * A server component, which a client one may render too: it holds no state and names its section
 * by `aria-label`, never by `useId` (#251).
 */
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** What the principal command of a card does: creates or triggers something, or modifies it. */
export type PrincipalDoes = "create" | "trigger" | "modify";

/** The variant of the button of the principal command of a card: filled, unless it modifies. */
export function principalVariant(does: PrincipalDoes): "default" | "outline" {
  return does === "modify" ? "outline" : "default";
}

/** The principal command of a card, and what it does. */
export interface Principal {
  readonly does: PrincipalDoes;
  /** The command, whose button takes `principalVariant(does)`. */
  readonly command: ReactNode;
}

/** What a card shows: its title, its commands, its body. */
export interface SectionCardProps {
  /** The title of the card, which names its section. */
  readonly title: string;
  readonly icon?: LucideIcon | undefined;
  /** What the card is for, under its title. */
  readonly description?: ReactNode;
  /** The other commands of the card, outlined, before its principal one. */
  readonly commands?: ReactNode;
  readonly principal?: Principal | undefined;
  readonly children: ReactNode;
}

/** Render a section of a screen in its card. */
export function SectionCard({
  title,
  icon: Icon,
  description,
  commands,
  principal,
  children,
}: SectionCardProps) {
  const commanded = commands !== undefined || principal !== undefined;
  return (
    <section aria-label={title} data-slot="section-card" className="min-w-0">
      <Card>
        <CardHeader className="flex flex-wrap items-start gap-x-4 gap-y-2">
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <CardTitle className="min-h-8 text-base">
              {Icon === undefined ? null : (
                <Icon aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
              )}
              {title}
            </CardTitle>
            {description === undefined ? null : <CardDescription>{description}</CardDescription>}
          </div>
          {commanded ? (
            <div
              data-slot="section-card-commands"
              className="flex flex-wrap items-start justify-end gap-2"
            >
              {commands}
              {principal === undefined ? null : (
                <div data-slot="section-card-principal" data-does={principal.does} className="flex">
                  {principal.command}
                </div>
              )}
            </div>
          ) : null}
        </CardHeader>
        <CardContent className="min-w-0">{children}</CardContent>
      </Card>
    </section>
  );
}
