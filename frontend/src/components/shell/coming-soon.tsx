// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The page of a function whose screen is still to come: its name, and that it is to come.
 * The lot of the screen replaces it by a page of its own, at the same route.
 */
import { useTranslations } from "next-intl";

import type { NavigationFunction } from "@/navigation/functions";

/** The function whose screen is to come. */
export interface ComingSoonProps {
  readonly label: NavigationFunction["label"];
}

/** Render the name of a function, and that its screen is to come. */
export function ComingSoon({ label }: ComingSoonProps) {
  const t = useTranslations();
  return (
    <main className="space-y-2 p-6">
      <h1 className="text-2xl font-semibold">{t(label)}</h1>
      <p className="text-muted-foreground">{t("screen.comingSoon")}</p>
    </main>
  );
}
