// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The languages of the interface, and how the language of a request is chosen
 * (WF-INTF-0160): the preference of the account when it names a language, else the first
 * offered language the browser asks for, else the default language of the installation.
 *
 * Pure: the server reads the three sources (`request.ts`), this module only decides. The
 * language never appears in the address: a shared link opens in the language of whoever
 * opens it (WF-INTF-0170).
 */
import type { components } from "@/api/generated/schema";

/** A language the interface is offered in: the `Language` of the contract. */
export type Locale = components["schemas"]["Language"];

/** The language preference of an account: `default` follows the browser. */
export type LanguagePreference = NonNullable<
  components["schemas"]["DisplayPreferences"]["language"]
>;

/** The offered languages, the reference catalogue first. */
export const LOCALES = ["fr", "en"] as const satisfies readonly Locale[];

/** The three values of the preference, in the order the selector offers them. */
export const PREFERENCES = ["default", ...LOCALES] as const satisfies readonly LanguagePreference[];

/**
 * The language of a request when the installation cannot tell its own: the language of the
 * reference catalogue. Reached only when `getInstallation` fails or cannot be reached.
 */
export const FALLBACK_LOCALE: Locale = "fr";

/** Whether a value names an offered language. */
export function isLocale(value: unknown): value is Locale {
  return LOCALES.some((locale) => locale === value);
}

/** Whether a value is one of the three values of the preference. */
export function isLanguagePreference(value: unknown): value is LanguagePreference {
  return PREFERENCES.some((preference) => preference === value);
}

// A range of Accept-Language names a language, or any (`*`); its weight goes from 0 to 1,
// three decimals at most (RFC 9110, §12.4.2).
const TAG = /^([a-z]{1,8}(-[a-z\d]{1,8})*|\*)$/i;
const WEIGHT = /^q=(0(\.\d{0,3})?|1(\.0{0,3})?)$/i;

/** A range of the header, or `undefined` when it is malformed. */
function range(part: string): { tag: string; weight: number } | undefined {
  const [tag = "", weight = "q=1"] = part.replaceAll(/\s/g, "").split(";");
  // A weight is no amount: reading it as a number loses nothing.
  return TAG.test(tag) && WEIGHT.test(weight)
    ? { tag: tag.toLowerCase(), weight: Number(weight.slice(2)) }
    : undefined;
}

/** The ranges of an Accept-Language header, most wanted first; malformed ones are dropped. */
function ranges(header: string): string[] {
  const wanted = header
    .split(",")
    .map(range)
    .filter((parsed) => parsed !== undefined)
    .filter((parsed) => parsed.weight > 0);
  // A stable sort: ranges of the same weight keep the order the browser gave them.
  return wanted.toSorted((a, b) => b.weight - a.weight).map((parsed) => parsed.tag);
}

/**
 * The offered language the browser asks for first, by its primary tag — `en-GB` asks for
 * `en`. `undefined` when it asks for none, or for any language (`*`) before an offered one:
 * the installation decides then.
 */
export function browserLocale(acceptLanguage: string | null | undefined): Locale | undefined {
  for (const tag of ranges(acceptLanguage ?? "")) {
    if (tag === "*") {
      return undefined;
    }
    const primary = tag.split("-")[0];
    if (isLocale(primary)) {
      return primary;
    }
  }
  return undefined;
}

/**
 * The language of a request, from the preference of the account and the Accept-Language
 * header; `undefined` when neither decides, and the default language of the installation
 * does.
 */
export function resolveLocale(
  preference: LanguagePreference | undefined,
  acceptLanguage: string | null | undefined,
): Locale | undefined {
  return isLocale(preference) ? preference : browserLocale(acceptLanguage);
}
