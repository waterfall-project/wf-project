// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The markup a page streams, read in two parts: its shell, up to a mark — what the address of a
 * filter waits for — and the rest, once what the test held back is released (US-2290, #3630).
 */
import type { ReactNode } from "react";
import { renderToReadableStream } from "react-dom/server";

/** What a page writes first, up to `mark`, and what it writes afterwards. */
export interface PageStream {
  readonly shell: string;
  /** The rest of the markup, read to the end: call it once what was held is released. */
  readonly rest: () => Promise<string>;
}

/** The markup without its comments: each one is cut by a scan, not by a pattern. */
function withoutComments(markup: string): string {
  let out = "";
  let from = 0;
  for (;;) {
    const open = markup.indexOf("<!--", from);
    if (open < 0) {
      return out + markup.slice(from);
    }
    out += markup.slice(from, open);
    const close = markup.indexOf("-->", open + 4);
    if (close < 0) {
      return out;
    }
    from = close + 3;
  }
}

/** The text of the markup, its tags and comments cut and replaced by one space each. */
export function textOfMarkup(markup: string): string {
  let out = "";
  let inTag = false;
  for (const char of withoutComments(markup)) {
    if (inTag) {
      if (char === ">") {
        inTag = false;
        out += " ";
      }
    } else if (char === "<") {
      inTag = true;
    } else {
      out += char;
    }
  }
  return out.replaceAll("&#x27;", "'");
}

/** What a page says, the comments of React and the escapes of its quotes left out. */
export function plain(markup: string): string {
  return withoutComments(markup).replaceAll("&#x27;", "'");
}

/**
 * Stream `element` and read it until `mark` is written: the shell as the browser gets it with the
 * document, its boundaries still waiting for what the test holds.
 */
export async function streamUntil(element: ReactNode, mark: string): Promise<PageStream> {
  const stream = await renderToReadableStream(element);
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let shell = "";
  while (!shell.includes(mark)) {
    const chunk = await reader.read();
    if (chunk.done) {
      throw new Error(`The page ended before it wrote ${mark}.`);
    }
    shell += decoder.decode(chunk.value as Uint8Array, { stream: true });
  }
  return {
    shell: plain(shell),
    rest: async () => {
      let rest = "";
      for (let chunk = await reader.read(); !chunk.done; chunk = await reader.read()) {
        rest += decoder.decode(chunk.value as Uint8Array, { stream: true });
      }
      return plain(rest);
    },
  };
}

/**
 * The markup of a screen whose summary streams apart from its grid, read once every boundary is
 * settled — each written in its place, whatever its size —, and a failure of what a boundary reads
 * thrown, as the shell would say it.
 */
export async function streamed(page: ReactNode): Promise<string> {
  const failures: unknown[] = [];
  const stream = await renderToReadableStream(page, {
    progressiveChunkSize: Infinity,
    onError: (failure) => {
      failures.push(failure);
    },
  });
  await stream.allReady;
  const markup = await new Response(stream).text();
  if (failures.length > 0) {
    throw failures[0];
  }
  return plain(markup);
}
