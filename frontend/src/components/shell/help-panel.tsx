// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The panel of the online help (WF-IHM-0140, US-0580): the button « Aide » of the header of a
 * screen, or F1 anywhere on it, opens beside the screen the page of the help of its code of the FBS —
 * the code of the route the address follows (`helpCodeAt`) —, read on the server when the panel
 * opens (`readHelp`). A screen whose address the table of the functions does not know — the
 * account, a page of the system — offers no help.
 *
 * The page is Markdown (`help-markdown.tsx`, loaded when the panel first shows a page): no raw
 * HTML, only the elements a page of text needs. A link to another page of the help — a screen, a
 * notion — shows that page in the panel, without leaving the screen; any other link shows as text.
 * The section of the columns is followed by the definitions of the columns of the grid, from the
 * catalogues, as their headers show them; a function's screen leads to the pages of its sections.
 * A search reads the titles of the pages written. A page not written yet says that its help is to
 * come. The help is in French alone (`HELP_LANGUAGE`): the title and the page, and the titles a
 * search finds, say so (`lang`) in an interface in another language, for a screen reader to speak
 * them as French; the messages of the interface around them keep its language. The body, which
 * scrolls, is a region, named like the title, that Tab reaches.
 *
 * The panel is a sheet: a dialog of Radix, named by its title, which holds the focus, closes by
 * Escape and gives the focus back to where it was — the button, or the cell where F1 was pressed. A
 * page shown by a link gives its title the focus, so that a screen reader says where it is.
 */
"use client";

import { ArrowLeft, CircleHelp, House, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  Component,
  lazy,
  type ReactNode,
  Suspense,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

import { readHelp } from "@/api/actions/help";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  COLUMNS_SECTION,
  fileOf,
  HELP_LANGUAGE,
  type HelpColumn,
  type HelpEntry,
  type HelpPage,
  type HelpReading,
  type HelpTarget,
  helpCodeAt,
  sameTarget,
  searched,
  sectionsOf,
} from "@/help/help";

import { HelpLink } from "./help-link";

/**
 * The renderer of the Markdown, loaded when the panel first shows a page: `react-markdown` and its
 * plugins are the weight of the help, which a screen whose help stays closed does not carry.
 */
const HelpMarkdown = lazy(async () => {
  const loaded = await import("./help-markdown");
  return { default: loaded.HelpMarkdown };
});

/**
 * The boundary of the renderer's chunk: a chunk that does not load (the network, a new deployment)
 * shows the failed reading in the body of the panel, not the error page of the route in the place
 * of the screen.
 */
class ChunkBoundary extends Component<
  { readonly failed: ReactNode; readonly children: ReactNode },
  { readonly error: boolean }
> {
  override state = { error: false };

  static getDerivedStateFromError() {
    return { error: true };
  }

  override render() {
    return this.state.error ? this.props.failed : this.props.children;
  }
}

/** The definitions of the columns of a grid, as its headers show them in their tooltips. */
function HelpColumns({ columns }: { readonly columns: readonly HelpColumn[] }) {
  const t = useTranslations("help");
  const headings = useTranslations("grid.columns");
  const definitions = useTranslations("columns");
  // The headers and the definitions are the interface's own: they stay out of the French page around them.
  const locale = useLocale();
  if (columns.length === 0) {
    return null;
  }
  return (
    <dl lang={locale} className="space-y-2">
      {columns.map((column) => (
        <div key={column.help}>
          <dt className="font-medium">
            {headings(column.label)}
            {column.computed ? (
              <span className="ml-1 font-normal text-muted-foreground">{t("computed")}</span>
            ) : null}
          </dt>
          <dd className="leading-relaxed">{definitions(`${column.help}.help`)}</dd>
        </div>
      ))}
    </dl>
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
  // The title of the list is the interface's own: it stays out of the French page around it.
  const locale = useLocale();
  const heading = useId();
  const parts = sectionsOf(code).flatMap((section) =>
    index.filter((entry) => sameTarget(entry.target, { kind: "screen", code: section })),
  );
  if (parts.length === 0) {
    return null;
  }
  return (
    <nav aria-labelledby={heading} lang={locale} className="space-y-1">
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

/** A page of the help written: its sections, the columns after theirs. */
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
    <div lang={HELP_LANGUAGE} className="space-y-5 text-sm">
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
          {at === COLUMNS_SECTION ? <HelpColumns columns={page.columns} /> : null}
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

/**
 * Whether the body shows the results of a search: a word is typed, and there is an index to read
 * them in — a reading failed or on its way, with no index yet, would answer « no page » to a word
 * it could not look for, and hide its own alert.
 */
function searching(query: string, index: readonly HelpEntry[], shown: Shown): boolean {
  return query.trim() !== "" && (index.length > 0 || shown.kind === "read");
}

/** The results of a search, each a link to its page: the count is the interface's own, the titles are French. */
function SearchResults({
  found,
  onFollow,
}: {
  readonly found: readonly HelpEntry[];
  readonly onFollow: (target: HelpTarget) => void;
}) {
  const t = useTranslations("help");
  return (
    <div className="space-y-2 text-sm">
      <p role="status">{t("results", { count: found.length })}</p>
      {found.length === 0 ? null : (
        <ul className="space-y-1">
          {found.map((entry) => (
            <li key={fileOf(entry.target)} lang={HELP_LANGUAGE}>
              <HelpLink target={entry.target} onFollow={onFollow}>
                {entry.title}
              </HelpLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * The button and the panel of the help of a screen, by its code. The button is an icon named
 * « Aide », at most as high as the line of a dense title (28 points), which it follows
 * (`page-header.tsx`); its tooltip says its name and F1.
 */
function ScreenHelp({ code }: { readonly code: string }) {
  const t = useTranslations();
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState<HelpTarget>({ kind: "screen", code });
  const [history, setHistory] = useState<readonly HelpTarget[]>([]);
  const [shown, setShown] = useState<Shown>({ kind: "loading" });
  const [index, setIndex] = useState<readonly HelpEntry[]>([]);
  const [query, setQuery] = useState("");
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
    setQuery("");
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
      // Where F1 was pressed; with nothing focused — the body — the button is where to go back.
      const active = document.activeElement;
      returnTo.current = active instanceof HTMLElement && active !== document.body ? active : null;
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
  const found = searched(index, query);

  return (
    <>
      <CommandTooltip label={t("help.button")} help={t("commands.help.help")} keys="F1">
        <Button
          ref={button}
          type="button"
          variant="outline"
          size="icon"
          className="size-7"
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-controls={open ? panelId : undefined}
          onClick={openScreen}
        >
          <CircleHelp aria-hidden="true" />
          <span className="sr-only">{t("help.button")}</span>
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
              lang={written?.kind === "written" ? HELP_LANGUAGE : undefined}
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
          <div className="border-b px-4 py-2">
            <Input
              type="search"
              aria-label={t("help.search")}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
              }}
            />
          </div>
          <div
            role="region"
            aria-label={heading}
            tabIndex={0}
            className="flex-1 overflow-y-auto p-4 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
          >
            {searching(query, index, shown) ? (
              <SearchResults found={found} onFollow={follow} />
            ) : shown.kind === "loading" ? (
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
              <ChunkBoundary
                failed={
                  <p role="alert" className="text-sm">
                    {t("help.failed")}
                  </p>
                }
              >
                <Suspense
                  fallback={
                    <p role="status" className="text-sm text-muted-foreground">
                      {t("help.loading")}
                    </p>
                  }
                >
                  <WrittenPage page={shown.reading.page} index={index} onFollow={follow} />
                </Suspense>
              </ChunkBoundary>
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
