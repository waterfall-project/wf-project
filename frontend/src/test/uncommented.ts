// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only

/** Where the comment that opens at `from` ends, or `from` when none opens there. */
function commentEnd(source: string, from: number): number {
  const opening = source.slice(from, from + 2);
  if (opening === "/*") {
    const end = source.indexOf("*/", from + 2);
    return end === -1 ? source.length : end + 2;
  }
  if (opening === "//") {
    const end = source.indexOf("\n", from);
    return end === -1 ? source.length : end;
  }
  return from;
}

/** Where the string that opens at `from` with `quote` ends: its quote, or its line if unclosed. */
function quotedEnd(source: string, from: number): number {
  const quote = source.charAt(from);
  let end = from + 1;
  while (end < source.length && source.charAt(end) !== quote && source.charAt(end) !== "\n") {
    end += source.charAt(end) === "\\" ? 2 : 1;
  }
  return source.charAt(end) === quote ? end + 1 : end;
}

/** Where the text of a template string read from `from` ends: after its backtick or its `${`. */
function templateEnd(source: string, from: number): number {
  let end = from;
  while (end < source.length) {
    const c = source.charAt(end);
    if (c === "`" || (c === "$" && source.charAt(end + 1) === "{")) {
      return c === "`" ? end + 1 : end + 2;
    }
    end += c === "\\" ? 2 : 1;
  }
  return source.length;
}

/**
 * A source without its comments, for the guards that read sources as text (#839): a directive, an
 * import or a name written in a comment is none. The strings — single, double, template — are
 * skipped before a comment is told, and kept as written: a `/*` or a `//` in a string opens
 * nothing, and the directives the guards look for are strings. A single or double quoted string
 * ends at its line, so that an apostrophe of a text in JSX costs one line at most. A regular
 * expression literal is not told from a division: one that holds a quote or a `/*` is out of reach.
 */
export function uncommented(source: string): string {
  let out = "";
  // The depth of the braces at each open substitution `${ … }` of a template string.
  const substitutions: number[] = [];
  let depth = 0;
  let i = 0;
  // Copy the text of a template string from `from`; a `${` that ends it opens a substitution.
  const template = (from: number) => {
    const end = templateEnd(source, from);
    out += source.slice(from, end);
    i = end;
    if (source.slice(end - 2, end) === "${") {
      substitutions.push(depth);
      depth += 1;
    }
  };
  while (i < source.length) {
    const c = source.charAt(i);
    const after = commentEnd(source, i);
    if (after > i) {
      i = after;
    } else if (c === '"' || c === "'") {
      const end = quotedEnd(source, i);
      out += source.slice(i, end);
      i = end;
    } else if (c === "`") {
      out += c;
      template(i + 1);
    } else if (c === "}" && substitutions.at(-1) === depth - 1) {
      substitutions.pop();
      depth -= 1;
      out += c;
      template(i + 1);
    } else {
      depth += c === "{" ? 1 : c === "}" ? -1 : 0;
      out += c;
      i += 1;
    }
  }
  return out;
}
