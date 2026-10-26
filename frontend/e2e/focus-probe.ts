// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The side of the walk by the keyboard that lives in the page (`tab-walk.ts`): what it notes as a
 * walk starts — what Tab may reach, the look of each before the focus comes, the widgets that move
 * the focus among their items —, what it measures of the element the focus is on, and what it finds
 * once the walk is over. Given to the page once, it stays there from one walk to the next.
 */
import type { Page } from "@playwright/test";

/**
 * Whether the focus of an element shows, settled once it is left: unknown when the element is gone
 * from the page by then.
 */
export interface Settled {
  readonly said: string;
  readonly marked: boolean | undefined;
}

/** Where the focus is after a press, as the page tells it, and what it settled of the one before. */
export type Focus = { readonly settled: Settled | undefined } & (
  | { readonly kind: "document" | "tools" }
  | {
      readonly kind: "element";
      readonly id: number;
      readonly said: string;
      /** Why the window does not show it, if it does not. */
      readonly unseen: string | undefined;
      /** What takes the pointer at its middle instead of it, if anything does. */
      readonly covered: string | undefined;
      /** Whether its focus shows; unknown until it is left, for an element born after the start. */
      readonly marked: boolean | undefined;
    }
);

/** What the page notes as a walk starts. */
export interface Start {
  /** The elements Tab may reach wholly beyond the edge of a box that hides what overflows it. */
  readonly clipped: string[];
  /** The links and buttons out of the order of the keyboard, in no widget that moves the focus. */
  readonly untabbable: string[];
}

/** What the page finds once a walk is over. */
export interface End {
  /** The elements Tab may reach that the walk never reached. */
  readonly missed: string[];
  /** The widgets that move the focus among their items, which the walk never entered. */
  readonly stopless: string[];
}

/** The side of a walk the page keeps. */
interface Probe {
  start: () => Start;
  focus: () => Focus;
  finish: () => End;
}

/** Give the page its side of the walk, if it has not got it yet. */
async function install(page: Page): Promise<void> {
  await page.evaluate(() => {
    const holder = window as unknown as { focusProbe?: Probe };
    if (holder.focusProbe !== undefined) {
      return;
    }
    const COMPOSITE = ["grid", "treegrid", "tree", "menu", "menubar", "listbox", "radiogroup"]
      .concat(["tablist", "toolbar"])
      .map((role) => `[role="${role}"]`)
      .join(", ");
    const FOCUSABLE =
      "a[href], area[href], button, input:not([type=hidden]), select, textarea, iframe, summary, [tabindex], [contenteditable]:not([contenteditable=false])";

    // An element by its role and its name: its label, the text it is labelled by, or its own.
    const say = (element: Element): string => {
      const role = element.getAttribute("role") ?? element.localName;
      const by = (element.getAttribute("aria-labelledby") ?? "")
        .split(" ")
        .map((id) => document.getElementById(id)?.textContent ?? "")
        .join(" ");
      const labels = "labels" in element ? (element.labels as NodeListOf<HTMLLabelElement>) : null;
      const name = [
        element.getAttribute("aria-label"),
        by,
        labels?.[0]?.textContent,
        element.getAttribute("title"),
        element.textContent,
      ].find((text) => typeof text === "string" && text.trim() !== "");
      return `${role} « ${(name ?? "").replace(/\s+/g, " ").trim().slice(0, 40)} »`;
    };

    // The opacity of a colour as the browser writes it: `transparent`, `rgba(…, a)`, `… / a)`.
    const alpha = (colour: string): number => {
      const slashed = /\/\s*([\d.]+)(%?)\s*\)$/.exec(colour);
      const four = /^rgba\(([^,]+,){3}\s*([\d.]+)\s*\)$/.exec(colour);
      if (colour === "transparent") {
        return 0;
      }
      if (slashed !== null) {
        return Number.parseFloat(slashed[1] ?? "1") / (slashed[2] === "%" ? 100 : 1);
      }
      return four === null ? 1 : Number.parseFloat(four[2] ?? "1");
    };

    // Whether an ancestor holds an element positioned so — fixed, absolute — or any other.
    const holdsFixed = (style: CSSStyleDeclaration) =>
      style.transform !== "none" ||
      style.perspective !== "none" ||
      style.filter !== "none" ||
      /paint|layout|strict|content/.test(style.contain) ||
      style.willChange.includes("transform");
    const holds = (position: string, style: CSSStyleDeclaration) => {
      if (position === "fixed") {
        return holdsFixed(style);
      }
      return position !== "absolute" || style.position !== "static" || holdsFixed(style);
    };

    // The boxes that clip an element, nearest first: the ancestors that hide what overflows them,
    // along the chain of the blocks that hold it — a fixed element escapes all but a transformed one.
    const clippers = (element: Element): Element[] => {
      const found: Element[] = [];
      let position = getComputedStyle(element).position;
      for (let parent = element.parentElement; parent !== null; parent = parent.parentElement) {
        const style = getComputedStyle(parent);
        if (holds(position, style)) {
          if (style.overflowX !== "visible" || style.overflowY !== "visible") {
            found.push(parent);
          }
          position = ["fixed", "absolute"].includes(style.position) ? style.position : "static";
        }
      }
      return found;
    };

    // What of the window an element may draw in: the window, cut by the padding box of each box
    // that clips it.
    interface Area {
      left: number;
      top: number;
      right: number;
      bottom: number;
    }
    const room = (element: Element): Area => {
      const area = { left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight };
      for (const clipper of clippers(element)) {
        const style = getComputedStyle(clipper);
        const box = clipper.getBoundingClientRect();
        const left = box.left + clipper.clientLeft;
        const top = box.top + clipper.clientTop;
        if (style.overflowX !== "visible") {
          area.left = Math.max(area.left, left);
          area.right = Math.min(area.right, left + clipper.clientWidth);
        }
        if (style.overflowY !== "visible") {
          area.top = Math.max(area.top, top);
          area.bottom = Math.min(area.bottom, top + clipper.clientHeight);
        }
      }
      return area;
    };
    const within = (part: Area, area: Area): Area | undefined => {
      const cut = {
        left: Math.max(part.left, area.left),
        top: Math.max(part.top, area.top),
        right: Math.min(part.right, area.right),
        bottom: Math.min(part.bottom, area.bottom),
      };
      return cut.right - cut.left >= 1 && cut.bottom - cut.top >= 1 ? cut : undefined;
    };
    const middle = (area: Area) => ({
      x: (area.left + area.right) / 2,
      y: (area.top + area.bottom) / 2,
    });

    // Whether an element hides what is under it: a background, a picture, a field.
    const opaque = (element: Element) => {
      const style = getComputedStyle(element);
      return (
        alpha(style.backgroundColor) > 0 ||
        style.backgroundImage !== "none" ||
        ["img", "svg", "canvas", "video", "input", "select", "textarea"].includes(element.localName)
      );
    };
    // Whether an element paints where it lies: opaque, or a text of its own.
    const paints = (element: Element) =>
      opaque(element) ||
      [...element.childNodes].some(
        (node) => node.nodeType === Node.TEXT_NODE && (node.textContent ?? "").trim() !== "",
      );
    // Whether what is found at a point is the element itself: it, its content, or its label.
    const itself = (element: Element, found: Element) =>
      element.contains(found) || (found instanceof HTMLLabelElement && found.control === element);

    // Whether two areas share any point, an edge or a corner counting.
    const overlaps = (one: Area, other: Area) =>
      one.left <= other.right &&
      other.left <= one.right &&
      one.top <= other.bottom &&
      other.top <= one.bottom;
    // An area grown by a point on each side, past the rounding of the boxes of the browser.
    const grown = ({ left, top, right, bottom }: Area): Area => ({
      left: left - 1,
      top: top - 1,
      right: right + 1,
      bottom: bottom + 1,
    });

    // The elements made to take the pointer at the points measured within the boxes of some
    // elements (`drawn`), while the page is measured: a layer the pointer passes through hides what
    // it covers all the same. Every point the measure asks the browser about lies within one of
    // those boxes — the middle of what the window shows of the element, the bands of an outline
    // or a shadow drawn inside it —, and only an element over one of them can be found there: the
    // others are left as they are. Only those that do not take the pointer are changed, and given
    // back as they were. A sheet over every element (`* { pointer-events: auto }`), added and taken
    // away at each press, had the browser restyle the whole page twice — three fifths of the time
    // of a press on a page of two thousand elements, the walk of the roles beyond a minute and a
    // half under the load of four workers (#1263); every element that did not take the pointer,
    // changed at each press, still kept the browser busy 18 of the 22 seconds of a width of that
    // walk, 3.3 of them restyling, against 10 seconds busy without any change. Every element is
    // read first, then those found written, never one after the other: `pointer-events` is
    // inherited, and a read after a write had the browser restyle the page again.
    const measured = <T>(drawn: readonly Element[], measure: () => T): T => {
      const boxes = drawn.map((element) => grown(element.getBoundingClientRect()));
      const changed: [ElementCSSInlineStyle, string, string][] = [
        ...document.querySelectorAll<HTMLElement | SVGElement>("*"),
      ]
        .filter((element) => getComputedStyle(element).pointerEvents !== "auto")
        .filter((element) => {
          const box = element.getBoundingClientRect();
          return boxes.some((around) => overlaps(box, around));
        })
        .map(({ style }) => [
          { style },
          style.getPropertyValue("pointer-events"),
          style.getPropertyPriority("pointer-events"),
        ]);
      for (const [{ style }] of changed) {
        style.setProperty("pointer-events", "auto", "important");
      }
      try {
        return measure();
      } finally {
        for (const [{ style }, value, priority] of changed) {
          if (value === "") {
            style.removeProperty("pointer-events");
          } else {
            style.setProperty("pointer-events", value, priority);
          }
        }
      }
    };

    // What paints first at a point, over an element or its content, a transparent layer passed;
    // `null` when the element is not drawn there at all.
    const over = (element: Element, x: number, y: number): Element | null | undefined => {
      for (const drawn of document.elementsFromPoint(x, y)) {
        if (itself(element, drawn)) {
          return undefined;
        }
        const tools = drawn.localName === "nextjs-portal";
        if (!tools && drawn.checkVisibility({ opacityProperty: true }) && paints(drawn)) {
          return drawn;
        }
      }
      return null;
    };

    // Why the window does not show an element: hidden, out of it, or under what paints over it.
    const unseen = (element: Element): string | undefined => {
      if (!element.checkVisibility({ opacityProperty: true, visibilityProperty: true })) {
        return "hidden or transparent";
      }
      const left = within(element.getBoundingClientRect(), room(element));
      if (left === undefined) {
        return "out of the window";
      }
      const { x, y } = middle(left);
      const hit = over(element, x, y);
      if (hit === null) {
        return "not drawn at its place";
      }
      return hit === undefined ? undefined : `under ${say(hit)}`;
    };

    // What takes the pointer at the middle of an element instead of it — a transparent layer that
    // catches the clicks —, the sheet of the pointer left off.
    const covered = (element: Element): string | undefined => {
      const left = within(element.getBoundingClientRect(), room(element));
      if (left === undefined) {
        return undefined;
      }
      const { x, y } = middle(left);
      const found = document.elementFromPoint(x, y);
      if (found === null || itself(element, found) || found.localName === "nextjs-portal") {
        return undefined;
      }
      return `under ${say(found)}`;
    };

    // The look of the focus of an element: its outline, its shadows.
    interface Look {
      outline: string;
      shadows: string[];
    }
    const look = (drawn: Element): Look => {
      const style = getComputedStyle(drawn);
      return {
        outline: [
          style.outlineStyle,
          style.outlineWidth,
          style.outlineColor,
          style.outlineOffset,
        ].join(" "),
        shadows: style.boxShadow === "none" ? [] : style.boxShadow.split(/,(?![^(]*\))/),
      };
    };

    // The four sides of a band around a box, from `inner` to `outer` outwards.
    const sides = (box: Area, inner: number, outer: number): Area[] =>
      outer <= inner
        ? []
        : [
            {
              left: box.left - outer,
              top: box.top - outer,
              right: box.right + outer,
              bottom: box.top - inner,
            },
            {
              left: box.left - outer,
              top: box.bottom + inner,
              right: box.right + outer,
              bottom: box.bottom + outer,
            },
            {
              left: box.left - outer,
              top: box.top - outer,
              right: box.left - inner,
              bottom: box.bottom + outer,
            },
            {
              left: box.right + inner,
              top: box.top - outer,
              right: box.right + outer,
              bottom: box.bottom + outer,
            },
          ];

    // Whether a side of a band inside an element shows: in what clips it, and, at its middle, not
    // under what hides it — what the element holds, or a positioned element over its outline.
    const showsInside = (drawn: Element, side: Area, hides: (held: Element) => boolean) => {
      const shown = within(side, room(drawn));
      if (shown === undefined) {
        return false;
      }
      const { x, y } = middle(shown);
      const stack = document.elementsFromPoint(x, y);
      const index = stack.indexOf(drawn);
      return index !== -1 && !stack.slice(0, index).some(hides);
    };
    const positioned = (held: Element) =>
      opaque(held) && getComputedStyle(held).position !== "static";

    // Whether an outline shows: drawn, not transparent, a side of it within what clips it — and,
    // inside the element, not under a positioned element, which paints over it.
    const outlineShows = (drawn: Element) => {
      const style = getComputedStyle(drawn);
      const width = Number.parseFloat(style.outlineWidth);
      const offset = Number.parseFloat(style.outlineOffset);
      if (style.outlineStyle === "none" || !(width > 0) || alpha(style.outlineColor) === 0) {
        return false;
      }
      const area = room(drawn);
      return sides(drawn.getBoundingClientRect(), offset, offset + width).some((side) =>
        offset + width <= 0
          ? showsInside(drawn, side, positioned)
          : within(side, area) !== undefined,
      );
    };

    // The padding box of an element, where an inset shadow is drawn.
    const padding = (drawn: Element): Area => {
      const box = drawn.getBoundingClientRect();
      const left = box.left + drawn.clientLeft;
      const top = box.top + drawn.clientTop;
      return { left, top, right: left + drawn.clientWidth, bottom: top + drawn.clientHeight };
    };

    // Whether a shadow shows: not transparent, spread or blurred, a side of it within what clips
    // it — and, an inset one, not painted over by what the element holds.
    const shadowShows = (drawn: Element, shadow: string) => {
      const colour = /^\s*([a-z-]+\([^)]*\)|[a-z]+|#[0-9a-f]+)/i.exec(shadow)?.[1] ?? "";
      const [, , blur = 0, spread = 0] = [...shadow.matchAll(/(-?[\d.]+)px/g)].map((match) =>
        Number.parseFloat(match[1] ?? "0"),
      );
      const extent = Math.max(blur, 0) + Math.max(spread, 0);
      if (alpha(colour) === 0 || extent === 0) {
        return false;
      }
      if (/\binset\b/.test(shadow)) {
        return sides(padding(drawn), -extent, 0).some((side) => showsInside(drawn, side, opaque));
      }
      const area = room(drawn);
      return sides(drawn.getBoundingClientRect(), 0, extent).some(
        (side) => within(side, area) !== undefined,
      );
    };

    // What of an element's look shows: its outline if it shows, the shadows that show.
    const shownLook = (drawn: Element): Look => {
      const now = look(drawn);
      return {
        outline: outlineShows(drawn) ? now.outline : "",
        shadows: now.shadows.filter((shadow) => shadowShows(drawn, shadow)),
      };
    };

    // Whether a look shown while focused differs from the one worn without the focus.
    const differs = (focused: Look, unfocused: Look) =>
      (focused.outline !== "" && focused.outline !== unfocused.outline) ||
      focused.shadows.some((shadow) => !unfocused.shadows.includes(shadow));

    // Whether the focus of an element shows, if a part of it has its look without the focus.
    const marked = (looks: Map<Element, Look>, unfocused: (drawn: Element) => Look | undefined) => {
      const known = [...looks].filter(([drawn]) => unfocused(drawn) !== undefined);
      return known.length === 0
        ? undefined
        : known.some(([drawn, focused]) => differs(focused, unfocused(drawn) ?? focused));
    };

    // Whether an element lies wholly beyond the edge of a box that hides what overflows it, along
    // one axis. A box the user scrolls is no such edge for what it would scroll to: past it, it is
    // that box which must be within the boxes around it.
    const axes = [
      {
        overflow: "overflowX",
        start: "left",
        size: "width",
        scroll: "scrollLeft",
        client: "clientWidth",
        border: "clientLeft",
      },
      {
        overflow: "overflowY",
        start: "top",
        size: "height",
        scroll: "scrollTop",
        client: "clientHeight",
        border: "clientTop",
      },
    ] as const;
    type Axis = (typeof axes)[number];
    // Where a box lies in what a clipper holds, its scrolling undone: from its start, its size.
    const placed = (target: Element, shift: number, clipper: Element, axis: Axis) => {
      const box = target.getBoundingClientRect();
      const from =
        box[axis.start] +
        shift -
        clipper.getBoundingClientRect()[axis.start] -
        clipper[axis.border] +
        clipper[axis.scroll];
      return { from, beyond: from + box[axis.size] <= 0 || from >= clipper[axis.client] };
    };
    const clippedAway = (element: Element) =>
      axes.some((axis) => {
        let target = element;
        let shift = 0;
        for (const clipper of clippers(element)) {
          const overflow = getComputedStyle(clipper)[axis.overflow];
          const scrolls = overflow === "auto" || overflow === "scroll";
          if (scrolls && placed(target, shift, clipper, axis).beyond) {
            target = clipper;
            shift = 0;
          } else if (scrolls) {
            shift += clipper[axis.scroll];
          } else if (overflow !== "visible" && placed(target, shift, clipper, axis).beyond) {
            return true;
          }
        }
        return false;
      });

    let baseline = new WeakMap<Element, Look>();
    let reachable: Element[] = [];
    let composites: Element[] = [];
    let reached: Element[] = [];
    let pending: { element: Element; said: string; looks: Map<Element, Look> } | undefined;
    const ids = new WeakMap<Element, number>();
    let next = 0;

    // Settle the element left without a look of it before the walk: the look it has now it is left.
    const settle = (current: Element | null): Settled | undefined => {
      const left = pending;
      if (left === undefined || left.element === current) {
        return undefined;
      }
      pending = undefined;
      return {
        said: left.said,
        marked: marked(left.looks, (drawn) => (drawn.isConnected ? look(drawn) : undefined)),
      };
    };
    // The identity of an element through the walks.
    const idOf = (element: Element) => {
      const id = ids.get(element) ?? next;
      if (id === next) {
        ids.set(element, id);
        next += 1;
      }
      return id;
    };
    const shown = (element: Element) =>
      element.isConnected && element.checkVisibility({ visibilityProperty: true });
    // Whether the walk reached an element: the focus on it, or in it for a widget that moves the
    // focus among its items.
    const entered = (element: Element) =>
      reached.includes(element) ||
      (element.matches(COMPOSITE) && reached.some((focused) => element.contains(focused)));

    holder.focusProbe = {
      start: () => {
        if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur();
        }
        reachable = [...document.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
          (element) =>
            element.tabIndex >= 0 &&
            !element.matches(":disabled") &&
            element.closest("[inert]") === null &&
            element.checkVisibility({ visibilityProperty: true }),
        );
        composites = [...document.querySelectorAll(COMPOSITE)].filter(
          (widget) => shown(widget) && widget.closest("[inert]") === null,
        );
        baseline = new WeakMap();
        for (const drawn of reachable.flatMap((element) => [element, ...element.children])) {
          baseline.set(drawn, look(drawn));
        }
        reached = [];
        pending = undefined;
        return {
          clipped: reachable.filter(clippedAway).map(say),
          untabbable: [...document.querySelectorAll<HTMLElement>("a[href], button")]
            .filter(
              (element) =>
                element.tabIndex < 0 &&
                !element.matches(":disabled") &&
                element.closest(COMPOSITE) === null &&
                element.closest("[inert]") === null &&
                element.checkVisibility({ visibilityProperty: true }),
            )
            .map(say),
        };
      },
      focus: (): Focus => {
        const element = document.activeElement;
        const settled = settle(element);
        if (element === null || element === document.body || element === document.documentElement) {
          return { kind: "document", settled };
        }
        if (element.localName === "nextjs-portal") {
          return { kind: "tools", settled };
        }
        const id = idOf(element);
        reached.push(element);
        const said = say(element);
        const caught = covered(element);
        const parts = [element, ...element.children];
        const { hidden, looks } = measured(parts, () => ({
          hidden: unseen(element),
          looks: new Map(parts.map((drawn) => [drawn, shownLook(drawn)] as const)),
        }));
        const now = baseline.has(element)
          ? marked(looks, (drawn) => baseline.get(drawn))
          : undefined;
        pending = now === undefined ? (pending ?? { element, said, looks }) : pending;
        return { kind: "element", settled, id, said, unseen: hidden, covered: caught, marked: now };
      },
      finish: () => ({
        missed: reachable.filter((element) => shown(element) && !entered(element)).map(say),
        stopless: composites
          .filter(
            (widget) =>
              shown(widget) &&
              !reached.some((focused) => widget === focused || widget.contains(focused)),
          )
          .map(say),
      }),
    };
  });
}

/** Start a walk: what the page lets Tab reach, before anything has the focus. */
export async function startWalk(page: Page): Promise<Start> {
  await install(page);
  return page.evaluate(() => (window as unknown as { focusProbe: Probe }).focusProbe.start());
}

/** Where the focus is, and whether the element it is on shows, and shows that it has it. */
export function focusNow(page: Page): Promise<Focus> {
  return page.evaluate(() => (window as unknown as { focusProbe: Probe }).focusProbe.focus());
}

/** End a walk: what Tab may reach and never reached, the widgets it never entered. */
export function finishWalk(page: Page): Promise<End> {
  return page.evaluate(() => (window as unknown as { focusProbe: Probe }).focusProbe.finish());
}
