// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The panel of the online help (WF-IHM-0140, US-0580): the button « Aide » of the header of a
 * screen, or F1 anywhere on it, opens beside the screen the page of the help of its code of the FBS —
 * the code of the route the address follows (`helpCodeAt`) —, read on the server when the panel
 * opens (`readHelp`). A screen whose address the table of the functions does not know — the
 * account, a page of the system — offers no help.
 *
 * The page is Markdown, rendered without any raw HTML (`skipHtml`), and only in the elements a page
 * of text needs: an image, a raw block, anything else is dropped. A link to another page of the help
 * — a screen, a notion — shows that page in the panel, without leaving the screen; any other link
 * shows as text. A function's screen leads to the pages of its sections. A page not written yet says
 * that its help is to come.
 *
 * The panel is a sheet: a dialog of Radix, named by its title, which holds the focus, closes by
 * Escape and gives the focus back to where it was — the button, or the cell where F1 was pressed. A
 * page shown by a link gives its title the focus, so that a screen reader says where it is.
 */
"use client";

import { ArrowLeft, CircleHelp, House, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  type MouseEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { readHelp } from "@/api/actions/help";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  fileOf,
  type HelpEntry,
  type HelpPage,
  type HelpReading,
  type HelpTarget,
  helpCodeAt,
  linkTarget,
  sameTarget,
  sectionsOf,
} from "@/help/help";

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

/** The class of a link of the help, which shows another page of it in the panel. */
const LINK =
  "rounded-sm text-primary underline underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** A link to another page of the help, followed in the panel. */
function HelpLink({
  target,
  onFollow,
  children,
}: {
  readonly target: HelpTarget;
  readonly onFollow: (target: HelpTarget) => void;
  readonly children: ReactNode;
}) {
  return (
    <a
      href={`#${fileOf(target)}`}
      className={LINK}
      onClick={(event: MouseEvent<HTMLAnchorElement>) => {
        event.preventDefault();
        onFollow(target);
      }}
    >
      {children}
    </a>
  );
}

/** The Markdown of a page of the help, its links resolved from the page it belongs to. */
function HelpMarkdown({
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

/** The sections of a function's screen whose pages are written, each a link to its page. */
function HelpParts({
  code,
  index,
  onFollow,
}: {
  readonly code: string;
  readonly index: readonly HelpEntry[];
  readonly onFollow: (target: HelpTarget) => void;
}) {
  const t = useTranslations("help");
  const heading = useId();
  const parts = sectionsOf(code).flatMap((section) =>
    index.filter((entry) => sameTarget(entry.target, { kind: "screen", code: section })),
  );
  if (parts.length === 0) {
    return null;
  }
  return (
    <nav aria-labelledby={heading} className="space-y-1">
      <h4 id={heading} className="font-medium">
        {t("sections")}
      </h4>
      <ul className="list-disc space-y-1 pl-5">
        {parts.map((entry) => (
          <li key={fileOf(entry.target)}>
            <HelpLink target={entry.target} onFollow={onFollow}>
              {entry.title}
            </HelpLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** A page of the help written: its sections. */
function WrittenPage({
  page,
  index,
  onFollow,
}: {
  readonly page: Extract<HelpPage, { kind: "written" }>;
  readonly index: readonly HelpEntry[];
  readonly onFollow: (target: HelpTarget) => void;
}) {
  const id = useId();
  const { target } = page;
  return (
    <div className="space-y-5 text-sm">
      {page.intro === "" ? null : (
        <HelpMarkdown from={target} text={page.intro} onFollow={onFollow} />
      )}
      {page.sections.map((section, at) => (
        <section
          key={section.heading}
          aria-labelledby={`${id}-${String(at)}`}
          className="space-y-2"
        >
          <h3 id={`${id}-${String(at)}`} className="text-base font-semibold">
            {section.heading}
          </h3>
          <HelpMarkdown from={target} text={section.body} onFollow={onFollow} />
          {at === 0 && target.kind === "screen" ? (
            <HelpParts code={target.code} index={index} onFollow={onFollow} />
          ) : null}
        </section>
      ))}
    </div>
  );
}

/** What the panel shows of the page asked: read, unreadable, or on its way. */
type Shown =
  | { readonly kind: "loading" }
  | { readonly kind: "failed" }
  | { readonly kind: "read"; readonly reading: HelpReading };

/** The button and the panel of the help of a screen, by its code. */
function ScreenHelp({ code }: { readonly code: string }) {
  const t = useTranslations();
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState<HelpTarget>({ kind: "screen", code });
  const [history, setHistory] = useState<readonly HelpTarget[]>([]);
  const [shown, setShown] = useState<Shown>({ kind: "loading" });
  const [index, setIndex] = useState<readonly HelpEntry[]>([]);
  const panelId = useId();
  // The page asked last: an answer to an earlier one, arriving after it, is dropped.
  const asked = useRef(0);
  // Whether the title takes the focus once the page asked is shown: a link was followed.
  const toTitle = useRef(false);
  const title = useRef<HTMLHeadingElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  // Where the focus was when the panel opened — the button, or the cell where F1 was pressed —,
  // which it goes back to on closing: the panel has no trigger of Radix to give it back to.
  const returnTo = useRef<HTMLElement | null>(null);

  const show = useCallback((target: HelpTarget, past: readonly HelpTarget[]) => {
    asked.current += 1;
    const ticket = asked.current;
    setPage(target);
    setHistory(past);
    setShown({ kind: "loading" });
    const answer = (next: Shown) => {
      if (ticket === asked.current) {
        setShown(next);
        if (next.kind === "read") {
          setIndex(next.reading.index);
        }
      }
    };
    readHelp(target).then(
      (reading) => {
        answer(reading === undefined ? { kind: "failed" } : { kind: "read", reading });
      },
      () => {
        answer({ kind: "failed" });
      },
    );
  }, []);

  const openScreen = useCallback(() => {
    if (!open) {
      returnTo.current =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
    }
    toTitle.current = false;
    setOpen(true);
    show({ kind: "screen", code }, []);
  }, [code, open, show]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (
        event.key !== "F1" ||
        event.ctrlKey ||
        event.altKey ||
        event.metaKey ||
        event.shiftKey ||
        event.defaultPrevented
      ) {
        return;
      }
      event.preventDefault();
      openScreen();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [openScreen]);

  useEffect(() => {
    if (shown.kind !== "loading" && toTitle.current) {
      toTitle.current = false;
      title.current?.focus();
    }
  }, [shown]);

  const follow = (target: HelpTarget) => {
    toTitle.current = true;
    show(target, [...history, page]);
  };
  const back = () => {
    const previous = history.at(-1);
    if (previous !== undefined) {
      toTitle.current = true;
      show(previous, history.slice(0, -1));
    }
  };
  const home = () => {
    toTitle.current = true;
    show({ kind: "screen", code }, []);
  };

  const written = shown.kind === "read" ? shown.reading.page : undefined;
  const heading = written?.kind === "written" ? written.title : t("help.title");
  const atScreen = sameTarget(page, { kind: "screen", code });

  return (
    <>
      <CommandTooltip label={t("help.button")} help={t("commands.help.help")} keys="F1">
        <Button
          ref={button}
          type="button"
          variant="outline"
          size="sm"
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-controls={open ? panelId : undefined}
          onClick={openScreen}
        >
          <CircleHelp aria-hidden="true" />
          {t("help.button")}
        </Button>
      </CommandTooltip>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          id={panelId}
          aria-describedby={undefined}
          className="w-full max-w-lg"
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            const back = returnTo.current;
            (back?.isConnected === true ? back : button.current)?.focus();
          }}
        >
          <SheetHeader className="flex-row items-center gap-2 border-b">
            <SheetTitle
              ref={title}
              tabIndex={-1}
              className="flex-1 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {heading}
            </SheetTitle>
            {history.length === 0 ? null : (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                aria-label={t("help.back")}
                onClick={back}
              >
                <ArrowLeft aria-hidden="true" />
              </Button>
            )}
            {atScreen ? null : (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                aria-label={t("help.screen")}
                onClick={home}
              >
                <House aria-hidden="true" />
              </Button>
            )}
            <SheetClose asChild>
              <Button type="button" variant="ghost" size="sm" aria-label={t("help.close")}>
                <X aria-hidden="true" />
              </Button>
            </SheetClose>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto p-4">
            {shown.kind === "loading" ? (
              <p role="status" className="text-sm text-muted-foreground">
                {t("help.loading")}
              </p>
            ) : shown.kind === "failed" ? (
              <p role="alert" className="text-sm">
                {t("help.failed")}
              </p>
            ) : shown.reading.page.kind === "pending" ? (
              <p className="text-sm">{t("help.pending")}</p>
            ) : (
              <WrittenPage page={shown.reading.page} index={index} onFollow={follow} />
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}

/**
 * The help of the screen the address shows: its button and its panel, or nothing where the table of
 * the functions knows no screen at the address.
 */
export function HelpPanel() {
  // Null outside the router of the application: a page rendered alone, in its test.
  const pathname = usePathname() as string | null;
  const code = pathname === null ? undefined : helpCodeAt(pathname);
  return code === undefined ? null : <ScreenHelp key={code} code={code} />;
}
