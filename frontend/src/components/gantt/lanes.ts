// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lanes of a timeline drawn as a frieze (US-0530, #1068): a calculation of presentation, which
 * deduces nothing the API says. Neither server nor client: the frieze reads it in the browser, its
 * tests in the project `node`.
 *
 * A rectangle takes the lane the user placed it in (`DisplayPreferences.timelines`), when it still
 * fits there; the others are stacked automatically, in the order of the plan, each in the first lane
 * where it overlaps no other. The lanes left empty are closed up, the top one being 0.
 *
 * A rectangle moves from lane to lane, and never into one where it would overlap another: the move
 * is refused, and nothing else moves. Below the last lane there is always an empty one, where a
 * rectangle fits; no lane is ever opened above another, which would move every rectangle below it.
 * The keyboard aims at the nearest lane up or down where the rectangle fits, passing those where it
 * would overlap, so that it reaches every lane the pointer reaches.
 */

/** A rectangle of the frieze: its task, where it starts and where it finishes, in milliseconds. */
export interface LaneSpan {
  readonly id: string;
  readonly from: number;
  readonly to: number;
}

/** The lane of each rectangle, by the identity of its task: 0 the top, without a gap. */
export type Lanes = ReadonlyMap<string, number>;

/** What a move comes to: the lanes moved, or why nothing moves. */
export type LaneMove =
  | { readonly kind: "moved"; readonly lanes: Lanes; readonly lane: number }
  | { readonly kind: "stayed" }
  | { readonly kind: "overlap"; readonly lane: number; readonly with: string }
  | { readonly kind: "edge"; readonly edge: "top" | "bottom" };

/** The most rectangles a timeline keeps the lane of (`TimelinePreferences.lanes`). */
export const KEPT_LANES = 64;

/** Whether two rectangles overlap: one starts before the other finishes, both ways. */
function overlaps(one: LaneSpan, other: LaneSpan): boolean {
  return one.from < other.to && other.from < one.to;
}

/** The first rectangle of a lane that one would overlap, itself left out; none if it fits. */
function blocker(
  spans: readonly LaneSpan[],
  lanes: Lanes,
  span: LaneSpan,
  lane: number,
): LaneSpan | undefined {
  return spans.find(
    (other) => other.id !== span.id && lanes.get(other.id) === lane && overlaps(span, other),
  );
}

/** The lanes renumbered from 0, in their order, those left empty closed up. */
function closedUp(lanes: Lanes): Map<string, number> {
  const used = [...new Set(lanes.values())].sort((one, other) => one - other);
  const rank = new Map(used.map((lane, at) => [lane, at]));
  return new Map([...lanes].map(([id, lane]) => [id, rank.get(lane) ?? 0]));
}

/**
 * The lanes of the rectangles, in the order of the plan: each placed one in its lane while it fits
 * there, then the others, and those placed where they no longer fit — their dates changed since —,
 * each in the first lane where it overlaps none.
 */
export function stackLanes(
  spans: readonly LaneSpan[],
  kept: Readonly<Record<string, number>> | undefined,
): Map<string, number> {
  const lanes = new Map<string, number>();
  const left: LaneSpan[] = [];
  for (const span of spans) {
    const placed = kept?.[span.id];
    if (placed !== undefined && placed >= 0 && blocker(spans, lanes, span, placed) === undefined) {
      lanes.set(span.id, placed);
    } else {
      left.push(span);
    }
  }
  for (const span of left) {
    let lane = 0;
    while (blocker(spans, lanes, span, lane) !== undefined) {
      lane += 1;
    }
    lanes.set(span.id, lane);
  }
  return closedUp(lanes);
}

/** How many lanes the rectangles take. */
export function laneCount(lanes: Lanes): number {
  return lanes.size === 0 ? 0 : Math.max(...lanes.values()) + 1;
}

/** Whether a rectangle is the only one of the last lane: it goes no lower. */
function aloneAtBottom(lanes: Lanes, id: string, lane: number): boolean {
  return (
    lane === laneCount(lanes) - 1 && [...lanes].every(([other, at]) => other === id || at !== lane)
  );
}

/** The lanes once a rectangle is in another, closed up. */
function placedIn(lanes: Lanes, id: string, lane: number): LaneMove {
  const moved = closedUp(new Map([...lanes, [id, lane]]));
  return { kind: "moved", lanes: moved, lane: moved.get(id) ?? lane };
}

/**
 * A rectangle moved to a lane, as the pointer drops it: within the lanes and the empty one below
 * them; refused where it would overlap another.
 */
export function movedTo(
  spans: readonly LaneSpan[],
  lanes: Lanes,
  id: string,
  target: number,
): LaneMove {
  const span = spans.find((each) => each.id === id);
  const lane = lanes.get(id);
  const aimed = Math.min(Math.max(target, 0), laneCount(lanes));
  if (span === undefined || lane === undefined || aimed === lane) {
    return { kind: "stayed" };
  }
  if (aimed === laneCount(lanes) && aloneAtBottom(lanes, id, lane)) {
    return { kind: "stayed" };
  }
  const other = blocker(spans, lanes, span, aimed);
  return other === undefined
    ? placedIn(lanes, id, aimed)
    : { kind: "overlap", lane: aimed, with: other.id };
}

/**
 * A rectangle moved a lane up or down, as the keyboard moves it: to the nearest lane that way where
 * it fits; refused at the top, at the bottom alone in its lane, and when it fits in no lane above —
 * the overlap named, that of the lane just above.
 */
export function movedBy(
  spans: readonly LaneSpan[],
  lanes: Lanes,
  id: string,
  step: 1 | -1,
): LaneMove {
  const span = spans.find((each) => each.id === id);
  const lane = lanes.get(id);
  if (span === undefined || lane === undefined) {
    return { kind: "stayed" };
  }
  const count = laneCount(lanes);
  if (step === 1 && aloneAtBottom(lanes, id, lane)) {
    return { kind: "edge", edge: "bottom" };
  }
  if (step === -1 && lane === 0) {
    return { kind: "edge", edge: "top" };
  }
  for (let aimed = lane + step; aimed >= 0 && aimed <= count; aimed += step) {
    if (blocker(spans, lanes, span, aimed) === undefined) {
      return placedIn(lanes, id, aimed);
    }
  }
  const first = blocker(spans, lanes, span, lane - 1);
  return { kind: "overlap", lane: lane - 1, with: first?.id ?? id };
}

/**
 * The lanes a timeline keeps once a rectangle is moved: those it shows, the moved one first, then
 * those the user had placed, then the others in the order of the plan. The frieze keeps them all;
 * `sentLanes` takes the part the preference holds.
 */
export function keptLanes(
  spans: readonly LaneSpan[],
  lanes: Lanes,
  moved: string,
  kept: Readonly<Record<string, number>> | undefined,
): Record<string, number> {
  const rank = (id: string) => {
    if (id === moved) {
      return 0;
    }
    return kept?.[id] === undefined ? 2 : 1;
  };
  const ordered = spans
    .map((span, at) => ({ id: span.id, at }))
    .sort((one, other) => rank(one.id) - rank(other.id) || one.at - other.at);
  return Object.fromEntries(ordered.map(({ id }) => [id, lanes.get(id) ?? 0]));
}

/**
 * The lanes sent to the account: the first of those kept — as many as the preference holds, beyond
 * which the last are stacked again automatically, once the page is read anew.
 */
export function sentLanes(kept: Readonly<Record<string, number>>): Record<string, number> {
  return Object.fromEntries(Object.entries(kept).slice(0, KEPT_LANES));
}
