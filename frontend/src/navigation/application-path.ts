// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Whether an address is a path of this front as it is written, before any resolution, which the way
 * back from the sign-in (`returnTarget`, #1429) and the screens of the history of the messages
 * (`isScreen`, #1181 point 5) share. It begins with one slash — never `//elsewhere`, which a browser
 * reads as another site —, and holds neither a backslash, which a browser reads as a slash
 * (`/\elsewhere`), nor a control character, U+0000 to U+001F and U+007F, of which a browser strips
 * the tabs and the line breaks: `/\t/elsewhere` is `//elsewhere` to it.
 */
export function isApplicationPath(address: string): boolean {
  return (
    address.startsWith("/") &&
    !address.startsWith("//") &&
    !address.includes("\\") &&
    !hasControlCharacter(address)
  );
}

const LAST_C0_CONTROL = 0x1f;
const DELETE = 0x7f;

// A loop, not a regular expression: `no-control-regex` forbids control characters in one.
function hasControlCharacter(text: string): boolean {
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index);
    if (code <= LAST_C0_CONTROL || code === DELETE) {
      return true;
    }
  }
  return false;
}
