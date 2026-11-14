// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The logo of the product. On the page — the bar above it, without a side bar —, in the variant of
 * the mode shown: the dark one where the workstation asks for a dark mode and the account lets it
 * decide, or where the account forces it; one image, whose source the browser picks — a screen
 * reader reads one name. On the side bar, dark in both modes, the dark one always.
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

/**
 * Render the logo on the side bar, midnight blue in both modes (EP-25, « La couleur ne vit que dans
 * les jetons »): its variant for a dark ground, whatever the mode of the page.
 */
export function BarLogo() {
  const t = useTranslations("app");
  // A picture without a source of its own, as the logo on the page: the file served as it is. The
  // picture is what lets a plain image pass `@next/next/no-img-element`, which no comment may
  // exempt; `next/image` would load the logo lazily and rewrite its attributes.
  return (
    <picture>
      <img src={DARK} alt={t("name")} width={123} height={32} className="h-8 w-auto" />
    </picture>
  );
}

/** Render the logo on the page, in the variant of the mode shown. */
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
