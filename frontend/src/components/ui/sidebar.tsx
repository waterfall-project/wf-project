// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The side bar of shadcn/ui, copied into the repository as far as the shell needs it: unfolded,
 * or folded into a rail of icons whose entries keep their names — a tooltip shows each on hover
 * and on the focus —; on a narrow screen, a sheet over the page, which closes once a link of it
 * is followed — to another page, to the same page with another query, to the page shown — and
 * once the address changes. Its state is kept as shadcn/ui keeps it, in a cookie (`sidebar-state.ts`),
 * and Ctrl+B or Cmd+B folds and unfolds it, while a bar is rendered. Folded, it gives the focus
 * of what the rail hides — a function of a block, the logo — to what stays: the block, or the
 * button that folds it.
 *
 * Adapted to the rules of the repository: its widths are tokens of the charter, not variables
 * set in a `style`; its texts come from the catalogue; its colours are the `sidebar-*` tokens,
 * measured; nothing moves as it folds. Its inset is a `<div>`, not a `<main>`: each page has
 * its own. Only what the shell renders is kept — neither the floating nor the inset variant,
 * nor the actions, badges and skeletons of an entry.
 */
"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { PanelLeft } from "lucide-react";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Slot } from "radix-ui";
import {
  type ComponentProps,
  createContext,
  type MouseEvent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";

import { Button } from "./button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "./sheet";
import { sidebarCookie } from "./sidebar-state";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";
import { cn } from "./utils";

/** A window narrower than this — the `md` of Tailwind — shows the bar as a sheet. */
const MOBILE = "(max-width: 767px)";

/** The key that folds and unfolds the bar, with Ctrl or Cmd. */
const SHORTCUT = "b";

/** What the rail hides: the functions of a block, the logo. */
const RAIL_HIDDEN = "data-rail-hidden";

/** What the bar and its pieces share: whether it is unfolded, and how to fold it. */
export interface SidebarState {
  readonly state: "expanded" | "collapsed";
  readonly open: boolean;
  readonly setOpen: (open: boolean) => void;
  readonly openMobile: boolean;
  readonly setOpenMobile: (open: boolean) => void;
  readonly isMobile: boolean;
  readonly toggleSidebar: () => void;
}

/**
 * What the provider shares, the width of the window left out: each piece reads it for itself
 * (`useIsMobile`). On a narrow screen, the window is known to be narrow only once in the browser,
 * after the server rendered the wide one; a context that changed then, above every page, would
 * make React render anew in the browser a page streamed by the server and not revealed yet,
 * beside the one the server sent (#173, #180).
 */
const SidebarContext = createContext<Omit<SidebarState, "isMobile"> | null>(null);

/** The state of the bar, within its provider; a piece of the bar outside it is a defect. */
export function useSidebar(): SidebarState {
  const context = useContext(SidebarContext);
  const isMobile = useIsMobile();
  if (context === null) {
    throw new Error("a piece of the side bar is rendered within a SidebarProvider only");
  }
  return { ...context, isMobile };
}

/** Listen to the width of the window crossing the width of a narrow screen. */
function subscribe(onChange: () => void): () => void {
  const query = window.matchMedia(MOBILE);
  query.addEventListener("change", onChange);
  return () => {
    query.removeEventListener("change", onChange);
  };
}

/** Whether the window is a narrow screen, now. */
function isNarrow(): boolean {
  return window.matchMedia(MOBILE).matches;
}

/** Whether the window is a narrow screen; not on the server, which renders the wide one. */
function useIsMobile(): boolean {
  return useSyncExternalStore(subscribe, isNarrow, () => false);
}

/**
 * Give the focus of what the rail is about to hide to what stays of it: the block of a function,
 * or else the button that folds the bar — never to the document.
 */
function keepFocus() {
  const active = document.activeElement;
  if (!(active instanceof HTMLElement) || active.closest(`[${RAIL_HIDDEN}]`) === null) {
    return;
  }
  const block = active
    .closest("[data-sidebar=menu-item]")
    ?.querySelector<HTMLElement>("[data-sidebar=menu-button]");
  (block ?? document.querySelector<HTMLElement>("[data-sidebar=trigger]"))?.focus();
}

/** Fold and unfold the bar with Ctrl+B or Cmd+B, wherever the focus is. */
function useShortcut(toggle: () => void) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === SHORTCUT && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [toggle]);
}

/** How the bar starts: unfolded or folded, as its cookie says. */
export interface SidebarProviderProps extends ComponentProps<"div"> {
  readonly defaultOpen?: boolean;
}

/** Hold the state of the bar for the bar and the page beside it. */
export function SidebarProvider({
  defaultOpen = true,
  className,
  children,
  ...props
}: SidebarProviderProps) {
  const [openMobile, setOpenMobile] = useState(false);
  // The sheet over the page closes once the user goes to another page: open, it would keep
  // the page hidden from a screen reader and hold the focus. Adjusted while rendering.
  const pathname = usePathname();
  const [shownAt, showAt] = useState(pathname);
  if (pathname !== shownAt) {
    showAt(pathname);
    setOpenMobile(false);
  }
  const [open, setOpenState] = useState(defaultOpen);
  const setOpen = useCallback((value: boolean) => {
    if (!value) {
      keepFocus();
    }
    setOpenState(value);
    document.cookie = sidebarCookie(value);
  }, []);
  // The width of the window is read as the bar is toggled, not held by the provider.
  const toggleSidebar = useCallback(() => {
    if (isNarrow()) {
      setOpenMobile((shown) => !shown);
    } else {
      setOpen(!open);
    }
  }, [open, setOpen]);
  const value = useMemo(
    () => ({
      state: open ? ("expanded" as const) : ("collapsed" as const),
      open,
      setOpen,
      openMobile,
      setOpenMobile,
      toggleSidebar,
    }),
    [open, setOpen, openMobile, toggleSidebar],
  );
  return (
    <SidebarContext value={value}>
      <TooltipProvider delayDuration={0}>
        <div
          data-slot="sidebar-wrapper"
          className={cn("group/sidebar-wrapper flex min-h-svh w-full", className)}
          {...props}
        >
          {children}
        </div>
      </TooltipProvider>
    </SidebarContext>
  );
}

/**
 * The bar: fixed along the left edge on a wide screen, a sheet on a narrow one; a landmark named
 * for it. The shortcut that folds it listens while it is rendered.
 */
export function Sidebar({ className, children, ...props }: ComponentProps<"div">) {
  const t = useTranslations("sidebar");
  const { isMobile, state, openMobile, setOpenMobile, toggleSidebar } = useSidebar();
  useShortcut(toggleSidebar);
  if (isMobile) {
    return (
      <Sheet open={openMobile} onOpenChange={setOpenMobile}>
        <SheetContent
          data-sidebar="sidebar"
          data-slot="sidebar"
          data-mobile="true"
          className="w-72 bg-sidebar p-0 text-sidebar-foreground"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>{t("label")}</SheetTitle>
            <SheetDescription>{t("description")}</SheetDescription>
          </SheetHeader>
          {/* A link followed closes the sheet, whatever it changes of the address; a link of a
              menu opened from the sheet, rendered elsewhere, reaches here through React. */}
          <div
            className="flex h-full w-full flex-col"
            onClick={(event) => {
              if (event.target instanceof Element && event.target.closest("a[href]") !== null) {
                setOpenMobile(false);
              }
            }}
          >
            {children}
          </div>
        </SheetContent>
      </Sheet>
    );
  }
  return (
    <aside
      aria-label={t("label")}
      className="group peer hidden text-sidebar-foreground md:block"
      data-state={state}
      data-collapsible={state === "collapsed" ? "icon" : ""}
      data-slot="sidebar"
    >
      <div
        data-slot="sidebar-gap"
        className="relative w-(--sidebar-width) group-data-[collapsible=icon]:w-(--sidebar-width-icon)"
      />
      <div
        data-slot="sidebar-container"
        className={cn(
          "fixed inset-y-0 left-0 z-10 hidden h-svh w-(--sidebar-width) border-r border-sidebar-border md:flex group-data-[collapsible=icon]:w-(--sidebar-width-icon)",
          className,
        )}
        {...props}
      >
        <div
          data-sidebar="sidebar"
          data-slot="sidebar-inner"
          className="flex h-full w-full flex-col bg-sidebar"
        >
          {children}
        </div>
      </div>
    </aside>
  );
}

/** The name of the control that folds or unfolds the bar, for the state it is in. */
export function useSidebarToggleLabel(): string {
  const t = useTranslations("sidebar");
  const { isMobile, open, openMobile } = useSidebar();
  return t((isMobile ? openMobile : open) ? "collapse" : "expand");
}

/** The button that folds and unfolds the bar, named for what it does now. */
export function SidebarTrigger({ className, onClick, ...props }: ComponentProps<typeof Button>) {
  const { isMobile, open, openMobile, toggleSidebar } = useSidebar();
  const label = useSidebarToggleLabel();
  return (
    <Button
      type="button"
      data-sidebar="trigger"
      data-slot="sidebar-trigger"
      variant="ghost"
      size="icon"
      aria-label={label}
      aria-expanded={isMobile ? openMobile : open}
      className={cn("size-7", className)}
      onClick={(event: MouseEvent<HTMLButtonElement>) => {
        onClick?.(event);
        toggleSidebar();
      }}
      {...props}
    >
      <PanelLeft aria-hidden="true" />
    </Button>
  );
}

/** The page beside the bar. */
export function SidebarInset({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-inset"
      className={cn("relative flex w-full min-w-0 flex-1 flex-col bg-background", className)}
      {...props}
    />
  );
}

/** The top of the bar. */
export function SidebarHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-header"
      data-sidebar="header"
      className={cn("flex flex-col gap-2 p-2", className)}
      {...props}
    />
  );
}

/** The foot of the bar. */
export function SidebarFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-footer"
      data-sidebar="footer"
      className={cn("flex flex-col gap-2 border-t border-sidebar-border p-2", className)}
      {...props}
    />
  );
}

/** The part of the bar that scrolls, between its top and its foot. */
export function SidebarContent({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-content"
      data-sidebar="content"
      className={cn(
        "flex min-h-0 flex-1 flex-col gap-1 overflow-x-hidden overflow-y-auto",
        className,
      )}
      {...props}
    />
  );
}

/** A group of entries of the bar. */
export function SidebarGroup({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-group"
      data-sidebar="group"
      className={cn("relative flex w-full min-w-0 flex-col p-2", className)}
      {...props}
    />
  );
}

/**
 * The label of a group, rendered as the heading it is given (`asChild`): folded into a rail,
 * it is hidden from the eye and stays for a screen reader.
 */
export function SidebarGroupLabel({
  className,
  asChild = false,
  ...props
}: ComponentProps<"div"> & { readonly asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "div";
  return (
    <Comp
      data-slot="sidebar-group-label"
      data-sidebar="group-label"
      className={cn(
        "flex h-7 shrink-0 items-center rounded-md px-2 text-xs font-medium text-muted-foreground",
        "group-data-[collapsible=icon]:sr-only",
        className,
      )}
      {...props}
    />
  );
}

/** A list of entries of the bar. */
export function SidebarMenu({ className, ...props }: ComponentProps<"ul">) {
  return (
    <ul
      data-slot="sidebar-menu"
      data-sidebar="menu"
      className={cn("flex w-full min-w-0 flex-col gap-0.5", className)}
      {...props}
    />
  );
}

/** An entry of the bar. */
export function SidebarMenuItem({ className, ...props }: ComponentProps<"li">) {
  return (
    <li
      data-slot="sidebar-menu-item"
      data-sidebar="menu-item"
      className={cn("group/menu-item relative", className)}
      {...props}
    />
  );
}

/** The classes of the control of an entry, by size: the page shown marked `aria-current`. */
export const sidebarMenuButtonVariants = cva(
  "peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm text-sidebar-foreground ring-sidebar-ring outline-hidden group-data-[collapsible=icon]:size-8! group-data-[collapsible=icon]:p-2! hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 aria-[current=page]:bg-sidebar-accent aria-[current=page]:font-medium aria-[current=page]:text-sidebar-accent-foreground aria-[current=true]:bg-sidebar-accent aria-[current=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0",
  {
    variants: {
      size: {
        default: "h-8",
        lg: "h-12 group-data-[collapsible=icon]:p-0!",
      },
    },
    defaultVariants: { size: "default" },
  },
);

/** The control of an entry, and the name its tooltip shows once the bar is a rail. */
export type SidebarMenuButtonProps = ComponentProps<"button"> &
  VariantProps<typeof sidebarMenuButtonVariants> & {
    /** Render the child — a link — rather than a button. */
    readonly asChild?: boolean;
    /** The name the tooltip shows once the bar is a rail. */
    readonly tooltip: string;
  };

/**
 * Render the control of an entry: its name in a tooltip once the bar is folded. Unfolded, or on
 * a narrow screen, the tooltip never opens — shadcn/ui opens it hidden, and a tooltip hidden
 * would still take the Escape meant for the sheet of the bar.
 */
export function SidebarMenuButton({
  asChild = false,
  size,
  tooltip,
  className,
  ...props
}: SidebarMenuButtonProps) {
  const Comp = asChild ? Slot.Root : "button";
  const { isMobile, state } = useSidebar();
  const [open, setOpen] = useState(false);
  const button = (
    <Comp
      data-slot="sidebar-menu-button"
      data-sidebar="menu-button"
      data-size={size ?? "default"}
      className={cn(sidebarMenuButtonVariants({ size }), className)}
      {...props}
    />
  );
  return (
    <Tooltip open={open && state === "collapsed" && !isMobile} onOpenChange={setOpen}>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent side="right" align="center">
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}

/** The entries under an entry — the functions of a block —, hidden once the bar is a rail. */
export function SidebarMenuSub({ className, ...props }: ComponentProps<"ul">) {
  return (
    <ul
      data-rail-hidden=""
      data-slot="sidebar-menu-sub"
      data-sidebar="menu-sub"
      className={cn(
        "mx-3.5 flex min-w-0 flex-col gap-0.5 border-l border-sidebar-border py-0.5 pl-2",
        "group-data-[collapsible=icon]:hidden",
        className,
      )}
      {...props}
    />
  );
}

/** An entry under an entry. */
export function SidebarMenuSubItem({ className, ...props }: ComponentProps<"li">) {
  return (
    <li
      data-slot="sidebar-menu-sub-item"
      data-sidebar="menu-sub-item"
      className={cn("relative", className)}
      {...props}
    />
  );
}

/** The link of an entry under an entry, the child it is given: the page shown `aria-current`. */
export function SidebarMenuSubButton({ className, ...props }: ComponentProps<typeof Slot.Root>) {
  return (
    <Slot.Root
      data-slot="sidebar-menu-sub-button"
      data-sidebar="menu-sub-button"
      className={cn(
        "flex h-7 min-w-0 items-center gap-2 overflow-hidden rounded-md px-2 text-sm text-sidebar-foreground ring-sidebar-ring outline-hidden hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 aria-[current=page]:bg-sidebar-accent aria-[current=page]:font-medium aria-[current=page]:text-sidebar-accent-foreground [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0",
        className,
      )}
      {...props}
    />
  );
}
