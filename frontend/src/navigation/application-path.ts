// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The guard of an address written by anyone that the front follows back to one of its screens: the
 * way back from the sign-in (`returnTarget` of `login.ts`, #1429) and the screens the history of the
 * messages keeps (`isScreen` of `message-history.ts`, #1181 point 5) share it, so neither lets
 * through what the other refuses.
 */

/** The last code of the controls of C0, U+0000 to U+001F. */
const LAST_C0_CONTROL = 0x1f;
/** The control DEL, U+007F. */
const DELETE = 0x7f;

/**
 * Whether an address is a path of this front as it is written, before any resolution: it begins
 * with one slash — never `//elsewhere`, which a browser reads as another site —, and holds neither a
 * backslash, which a browser reads as a slash (`/\elsewhere`), nor a control character, U+0000 to
 * U+001F and U+007F, of which a browser strips the tabs and the line breaks: `/\t/elsewhere` is
 * `//elsewhere` to it.
 */
export function isApplicationPath(address: string): boolean {
  return (
    address.startsWith("/") &&
    !address.startsWith("//") &&
    !address.includes("\\") &&
    !hasControlCharacter(address)
  );
}

/** Whether a text holds a control character, U+0000 to U+001F or U+007F. */
function hasControlCharacter(text: string): boolean {
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index);
    if (code <= LAST_C0_CONTROL || code === DELETE) {
      return true;
    }
  }
  return false;
}
