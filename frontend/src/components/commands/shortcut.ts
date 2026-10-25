// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The keys of a command, written once, as `aria-keyshortcuts` names them — `"Control+Z Meta+Z"`,
 * each way of pressing it apart by a space, each key of a way by a plus (WAI-ARIA 1.2) —, and what
 * the screen shows of them: the same text read for the eye, the way of the workstation alone — Cmd
 * on a Mac, Ctrl elsewhere — and each key by its name in the catalogue (`commands.keys`). Whoever
 * sets the attribute shows these keys, and the two cannot part (US-0580, #1071).
 */

/** The workstation, as far as its keys are written differently: a Mac, or any other. */
export type Platform = "mac" | "other";

/** The keys the catalogue names; any other — a letter, a sign, F10 — is shown as it is named. */
export const NAMED_KEYS = [
  "Control",
  "Meta",
  "Alt",
  "Shift",
  "Insert",
  "Delete",
  "ArrowLeft",
  "ArrowRight",
  "ArrowUp",
  "ArrowDown",
  "Plus",
  "ContextMenu",
  "Escape",
  "Enter",
] as const;

/** A key the catalogue names. */
export type NamedKey = (typeof NAMED_KEYS)[number];

/** The keys of the modifiers, which a Mac writes by their sign, the ones against the others. */
const MODIFIERS: ReadonlySet<string> = new Set(["Control", "Meta", "Alt", "Shift"]);

/** Whether a key is one the catalogue names. */
export function isNamedKey(key: string): key is NamedKey {
  return (NAMED_KEYS as readonly string[]).includes(key);
}

/** Whether a key is a modifier, which a Mac writes against the next key. */
export function isModifier(key: string): boolean {
  return MODIFIERS.has(key);
}

/**
 * The ways of pressing a command the workstation shows, each the keys pressed together: where the
 * keys name one way with Ctrl and another with Cmd, a Mac shows the one with Cmd, any other the one
 * with Ctrl; nothing for no keys.
 */
export function shownWays(keys: string | undefined, platform: Platform): string[][] {
  const ways = (keys ?? "")
    .split(" ")
    .filter((way) => way !== "")
    .map((way) => way.split("+"));
  const withMeta = ways.filter((way) => way.includes("Meta"));
  if (platform === "mac") {
    // Ctrl is the Mac's too, where no way with Cmd stands for it: Ctrl+Insert stays.
    const meant = new Set(withMeta.map((way) => replaced(way, "Meta", "Control").join("+")));
    return ways.filter((way) => !meant.has(way.join("+")));
  }
  return withMeta.length === ways.length ? ways : ways.filter((way) => !way.includes("Meta"));
}

/** A way of pressing with one key in place of another. */
function replaced(way: readonly string[], from: string, to: string): string[] {
  return way.map((key) => (key === from ? to : key));
}

/** Whether the browser runs on a Mac, whose keys are written by their signs, Cmd for Ctrl. */
export function onMac(): boolean {
  const nav = navigator as Navigator & { readonly userAgentData?: { readonly platform?: string } };
  return /mac|iphone|ipad/i.test(nav.userAgentData?.platform ?? nav.userAgent);
}
