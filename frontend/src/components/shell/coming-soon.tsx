// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The page of a screen still to come — a function of the navigation —, in the template of a
 * screen: its name and its icon, that it is to come, and the commands it already shows. The lot
 * of the screen replaces it by a page of its own, at the same route.
 */
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { NavigationFunction } from "@/navigation/functions";

import { type Density, PageHeader, Screen } from "./page-header";

/** The screen to come, and what the page shows of it already. */
export interface ComingSoonProps {
  readonly label: NavigationFunction["label"];
  readonly icon: LucideIcon;
  readonly density?: Density;
  /** The commands the screen offers already. */
  readonly children?: ReactNode;
}

/** Render the name of a screen, and that it is to come. */
export function ComingSoon({ label, icon, density = "dense", children }: ComingSoonProps) {
  const t = useTranslations();
  return (
    <Screen density={density}>
      <PageHeader
        title={t(label)}
        icon={icon}
        subtitle={t("screen.comingSoon")}
        actions={children}
        density={density}
      />
    </Screen>
  );
}
