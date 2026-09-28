// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The logo of the product, in the variant of the mode shown: the dark one where the
 * workstation asks for a dark mode and the account lets it decide, or where the account
 * forces it. One image, whose source the browser picks — a screen reader reads one name.
 */
import { useTranslations } from "next-intl";

import { forcedTheme, type ThemePreference } from "@/theme/theme";

// The two variants of docs/assets, served from public/; src/theme/brand.test.ts keeps them
// the same.
const LIGHT = "/waterfall_logo.svg";
const DARK = "/waterfall_logo-dark.svg";

// When the dark variant applies: never, always, or as the workstation says.
const DARK_WHEN = { light: undefined, dark: "all", default: "(prefers-color-scheme: dark)" };

/** The display mode preference of the account; `undefined` without an account. */
export interface LogoProps {
  readonly theme: ThemePreference | undefined;
}

/** Render the logo in the variant of the mode shown. */
export function Logo({ theme }: LogoProps) {
  const t = useTranslations("app");
  const media = DARK_WHEN[forcedTheme(theme) ?? "default"];
  return (
    <picture>
      {media === undefined ? null : <source srcSet={DARK} media={media} />}
      <img src={LIGHT} alt={t("name")} width={123} height={32} className="h-8 w-auto" />
    </picture>
  );
}
