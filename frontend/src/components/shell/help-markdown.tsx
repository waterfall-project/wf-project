// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The Markdown of a page of the help (WF-IHM-0140, US-0580), rendered without any raw HTML
 * (`skipHtml`) and only in the elements a page of text needs: an image, a raw block, anything else
 * is dropped. A link to another page of the help is followed in the panel; any other shows as text.
 * Loaded when the panel opens (`help-panel.tsx`), so that the renderer and its plugins weigh on no
 * screen that does not open its help.
 */
"use client";

import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { type HelpTarget, linkTarget } from "@/help/help";

import { HelpLink } from "./help-link";

/** The elements a page of the help is rendered in; any other is dropped, its text kept. */
const ALLOWED = [
  "p",
  "a",
  "strong",
  "em",
  "del",
  "code",
  "ul",
  "ol",
  "li",
  "blockquote",
  "h3",
  "h4",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
  "br",
  "hr",
];

/** The Markdown of a page of the help, its links resolved from the page it belongs to. */
export function HelpMarkdown({
  from,
  text,
  onFollow,
}: {
  readonly from: HelpTarget;
  readonly text: string;
  readonly onFollow: (target: HelpTarget) => void;
}) {
  const components: Components = {
    a: ({ href, children }) => {
      const target = href === undefined ? undefined : linkTarget(from, href);
      return target === undefined ? (
        <span>{children}</span>
      ) : (
        <HelpLink target={target} onFollow={onFollow}>
          {children}
        </HelpLink>
      );
    },
    p: ({ children }) => <p className="leading-relaxed">{children}</p>,
    ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
    ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
    blockquote: ({ children }) => (
      <blockquote className="border-l-2 pl-3 text-muted-foreground">{children}</blockquote>
    ),
    // A key, or a sequence of keys, is written as code in the Markdown.
    code: ({ children }) => (
      <kbd className="rounded border bg-muted px-1 font-sans text-xs">{children}</kbd>
    ),
    h3: ({ children }) => <h4 className="font-medium">{children}</h4>,
    h4: ({ children }) => <h5 className="font-medium">{children}</h5>,
    table: ({ children }) => <table className="w-full border-collapse">{children}</table>,
    th: ({ children }) => <th className="border px-2 py-1 text-left font-medium">{children}</th>,
    td: ({ children }) => <td className="border px-2 py-1 align-top">{children}</td>,
  };
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      allowedElements={ALLOWED}
      unwrapDisallowed
      components={components}
    >
      {text}
    </Markdown>
  );
}
