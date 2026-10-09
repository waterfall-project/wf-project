// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The name of the file an answer of the API gives as an attachment (`Content-Disposition`,
 * RFC 6266): the result of a background task, which the contract promises named
 * (`getBackgroundTaskResult`), a backup downloaded (`downloadBackup`); and the attachment the
 * front hands such a file on as (`attachment`).
 */

/** A parameter of the header: `name=value`, the value a token or a quoted string. */
const PARAMETER = /;\s*([!#$%&'*+.^`|~\w-]+)\s*=\s*("(?:[^"\\]|\\.)*"|[^;\s]*)/g;

/** An extended value (RFC 8187): its charset, its language, and its value encoded in percent. */
const EXTENDED = /^([!#$&+^`{}~\w-]+)'[\w-]*'(.*)$/;

/** A quoted string without its quotes, its escaped characters as they are. */
function unquoted(value: string): string {
  return value.startsWith('"') ? value.slice(1, -1).replace(/\\(.)/g, "$1") : value;
}

/** An extended value decoded, when it is in UTF-8 and well encoded; `undefined` otherwise. */
function decoded(value: string): string | undefined {
  const parts = EXTENDED.exec(value);
  if (parts?.[1]?.toLowerCase() !== "utf-8") {
    return undefined;
  }
  try {
    return decodeURIComponent(parts[2] ?? "");
  } catch {
    return undefined;
  }
}

/**
 * The name of the attached file: `filename*` when the header gives one the front can read — a name
 * that is not in ASCII, in UTF-8 —, `filename` otherwise, its ASCII equivalent; none for a header
 * that is no attachment, or names no file. A name is a base name: a path in it is cut away, so
 * that nothing saves the file elsewhere than the browser decides.
 */
export function attachmentName(disposition: string): string | undefined {
  if (!/^\s*attachment\s*(;|$)/i.test(disposition)) {
    return undefined;
  }
  const parameters = new Map<string, string>();
  for (const [, name, value] of disposition.matchAll(PARAMETER)) {
    if (name !== undefined && value !== undefined && !parameters.has(name.toLowerCase())) {
      parameters.set(name.toLowerCase(), value);
    }
  }
  const extended = parameters.get("filename*");
  const plain = parameters.get("filename");
  const name =
    (extended === undefined ? undefined : decoded(extended)) ??
    (plain === undefined ? undefined : unquoted(plain));
  const base = name?.split(/[/\\]/).at(-1)?.trim();
  return base === undefined || base === "" ? undefined : base;
}

/** A value of an extended parameter (RFC 8187): UTF-8, encoded in percent. */
function extendedValue(name: string): string {
  return encodeURIComponent(name).replace(
    /['()*]/g,
    (letter) => `%${letter.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

/** The attachment of a file under its name, its ASCII equivalent first (RFC 6266). */
export function attachment(name: string): string {
  const ascii = name.replace(/[^\x20-\x7e]|["\\]/g, "_");
  return `attachment; filename="${ascii}"; filename*=UTF-8''${extendedValue(name)}`;
}
