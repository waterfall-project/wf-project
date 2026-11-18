// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The indicators a screen reads apart from its grid never hold back the navigation of a filter
 * (US-2290, #3630). React's rule is proven here on its own — a boundary already revealed retains
 * the transition that makes its content suspend — then the remedy, `Streamed`, which keeps the
 * content shown and lets the grid and the address through. The router of Next navigates in a
 * transition, as these tests do.
 */
import { act, render, screen } from "@testing-library/react";
import {
  Component,
  type ReactNode,
  Suspense,
  startTransition,
  use,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { describe, expect, it } from "vitest";

import { takeStderr } from "@/test/stderr";

import { Streamed } from "./streamed";

/** A promise settled from outside, as an API read the test holds. */
function held<Value>() {
  let resolve: (value: Value) => void = () => undefined;
  let reject: (reason: Error) => void = () => undefined;
  const promise = new Promise<Value>((ok, no) => {
    resolve = ok;
    reject = no;
  });
  return { promise, resolve, reject };
}

/** Run what changes the screen inside `act`, awaited: a render may suspend in it. */
async function inAct(work: () => void) {
  await act(async () => {
    work();
    await Promise.resolve();
  });
}

/**
 * Let the promises settled and the retries of React that follow them run, past the delay by which
 * React throttles the reveal of a boundary that showed its fallback.
 */
async function settle() {
  await act(async () => {
    await new Promise((done) => setTimeout(done, 350));
  });
}

interface Reading {
  readonly scope: string;
  readonly content: Promise<ReactNode>;
}

interface Page {
  readonly grid: string;
  readonly content: Promise<ReactNode>;
}

/** A screen as the page makes it: a grid, and its indicators in a boundary of their own. */
function Screen({
  start,
  indicators,
  expose,
}: {
  readonly start: Page;
  readonly indicators: (content: Promise<ReactNode>) => ReactNode;
  readonly expose: (set: Dispatch<SetStateAction<Page>>) => void;
}) {
  const [page, setPage] = useState(start);
  expose(setPage);
  return (
    <>
      <p>{`grid ${page.grid}`}</p>
      <Suspense fallback={<p>loading</p>}>{indicators(page.content)}</Suspense>
    </>
  );
}

/** The read of a content by the render itself, as a boundary of suspense without `Streamed` does. */
function Plain({ content }: { readonly content: Promise<ReactNode> }) {
  return use(content);
}

/** Mount the screen on its first reading, once read and shown. */
async function mounted(indicators: (content: Promise<ReactNode>) => ReactNode) {
  const first = held<ReactNode>();
  let set: Dispatch<SetStateAction<Page>> = () => undefined;
  await inAct(() => {
    render(
      <Screen
        start={{ grid: "1", content: first.promise }}
        indicators={indicators}
        expose={(setter) => {
          set = setter;
        }}
      />,
    );
  });
  expect(screen.getByText("loading")).toBeTruthy();
  await inAct(() => {
    first.resolve("figures 1");
  });
  await settle();
  expect(screen.getByText("figures 1")).toBeTruthy();
  return {
    navigate: async (page: Page) => {
      await inAct(() => {
        startTransition(() => {
          set(page);
        });
      });
    },
  };
}

describe("a boundary of suspense revealed, in the transition of a filter", () => {
  it("retains the grid and the address while its content is read again: the rule Streamed gets around (US-2290)", async () => {
    const { navigate } = await mounted((content) => <Plain content={content} />);
    const next = held<ReactNode>();
    await navigate({ grid: "2", content: next.promise });
    // The grid of the new address is not shown, nor the fallback: the transition waits.
    expect(screen.getByText("grid 1")).toBeTruthy();
    expect(screen.queryByText("grid 2")).toBeNull();
    expect(screen.queryByText("loading")).toBeNull();
    await inAct(() => {
      next.resolve("figures 2");
    });
    await settle();
    expect(screen.getByText("grid 2")).toBeTruthy();
  });

  it("lets the grid of a filter through at once, the indicators shown until the new ones are read, then replaced [US-2290]", async () => {
    const { navigate } = await mounted((content) => <Streamed content={content} />);
    const next = held<ReactNode>();
    await navigate({ grid: "2", content: next.promise });
    expect(screen.getByText("grid 2")).toBeTruthy();
    expect(screen.getByText("figures 1")).toBeTruthy();
    expect(screen.queryByText("loading")).toBeNull();
    await inAct(() => {
      next.resolve("figures 2");
    });
    await settle();
    expect(screen.getByText("figures 2")).toBeTruthy();
    expect(screen.queryByText("figures 1")).toBeNull();
  });

  it("keeps the last content read when two navigations follow, and ignores the older one arriving late [US-2290]", async () => {
    const { navigate } = await mounted((content) => <Streamed content={content} />);
    const older = held<ReactNode>();
    const newer = held<ReactNode>();
    await navigate({ grid: "2", content: older.promise });
    await navigate({ grid: "3", content: newer.promise });
    await inAct(() => {
      newer.resolve("figures 3");
    });
    await settle();
    await inAct(() => {
      older.resolve("figures 2");
    });
    await settle();
    expect(screen.getByText("grid 3")).toBeTruthy();
    expect(screen.getByText("figures 3")).toBeTruthy();
    expect(screen.queryByText("figures 2")).toBeNull();
  });

  it("shows the fallback again under a boundary with another key: the figures of another reading are not kept [US-2290]", async () => {
    const first = held<ReactNode>();
    let set: Dispatch<SetStateAction<Reading>> = () => undefined;
    function Scoped({
      expose,
    }: {
      readonly expose: (setter: Dispatch<SetStateAction<Reading>>) => void;
    }) {
      const [page, setPage] = useState({ scope: "a", content: first.promise });
      expose(setPage);
      return (
        <Suspense key={page.scope} fallback={<p>loading</p>}>
          <Streamed content={page.content} />
        </Suspense>
      );
    }
    await inAct(() => {
      render(
        <Scoped
          expose={(setter) => {
            set = setter;
          }}
        />,
      );
    });
    await inAct(() => {
      first.resolve("figures a");
    });
    await settle();
    expect(screen.getByText("figures a")).toBeTruthy();
    const next = held<ReactNode>();
    await inAct(() => {
      startTransition(() => {
        set({ scope: "b", content: next.promise });
      });
    });
    expect(screen.getByText("loading")).toBeTruthy();
    expect(screen.queryByText("figures a")).toBeNull();
  });

  it("throws the failure of a content read after the first to the error boundary, as the first [US-2290]", async () => {
    class Boundary extends Component<{ children: ReactNode }, { failure: string | undefined }> {
      override state = { failure: undefined as string | undefined };
      static getDerivedStateFromError(error: Error) {
        return { failure: error.message };
      }
      override render() {
        return this.state.failure === undefined ? this.props.children : <p>{this.state.failure}</p>;
      }
    }
    const { navigate } = await mounted((content) => (
      <Boundary>
        <Streamed content={content} />
      </Boundary>
    ));
    const next = held<ReactNode>();
    await navigate({ grid: "2", content: next.promise });
    await inAct(() => {
      next.reject(new Error("service down"));
    });
    await settle();
    expect(screen.getByText("service down")).toBeTruthy();
    // React logs the error it handed to the boundary: that is what the test expects of it.
    expect(takeStderr().join("\n")).toContain("service down");
    expect(screen.getByText("grid 2")).toBeTruthy();
  });
});
