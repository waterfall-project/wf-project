// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { PAGE_LIMIT, type PageAnswered, type PageAsked, readEveryPage } from "./every-page";
import { type Answer, UnexpectedAnswer } from "./problem";

type Revision = components["schemas"]["Revision"];
type Revisions = PageAnswered<Revision>;

/** The revisions of the example of the contract: three of them. */
const REVISIONS = example("revisions") as Revisions;

/** A server that pages the revisions by `limit` at most, whatever page size it is asked. */
function paging(limit: number, pages: PageAsked[]) {
  return (page: PageAsked): Promise<Answer<Revisions>> => {
    pages.push(page);
    const items = REVISIONS.items.slice(page.offset, page.offset + Math.min(limit, page.limit));
    const meta = { limit: Math.min(limit, page.limit), offset: page.offset, total: 3 };
    return Promise.resolve({ data: { items, meta }, response: Response.json({ items, meta }) });
  };
}

describe("a list read whole", () => {
  it("asks the largest page the contract takes, and stops at a page that holds the rest", async () => {
    const pages: PageAsked[] = [];
    const read = await readEveryPage("listRevisions", paging(PAGE_LIMIT, pages));
    expect(read).toEqual(REVISIONS.items);
    expect(pages).toEqual([{ limit: 500, offset: 0 }]);
  });

  it("reads the pages one after the other until the total the server says is reached", async () => {
    const pages: PageAsked[] = [];
    const read = await readEveryPage("listRevisions", paging(2, pages));
    expect(read).toEqual(REVISIONS.items);
    expect(pages).toEqual([
      { limit: 500, offset: 0 },
      { limit: 500, offset: 2 },
    ]);
  });

  it("stops at a page that comes empty before the total, rather than asking for ever", async () => {
    const pages: PageAsked[] = [];
    const server = paging(2, pages);
    const read = await readEveryPage("listRevisions", async (page) => {
      const answer = await server(page);
      const data = answer.data ?? REVISIONS;
      return { ...answer, data: { items: data.items, meta: { ...data.meta, total: 10 } } };
    });
    expect(read).toEqual(REVISIONS.items);
    expect(pages).toHaveLength(3);
  });

  it("follows the rule of the reads a screen cannot do without on a refusal", async () => {
    const refused = (): Promise<Answer<Revisions>> =>
      Promise.resolve({
        error: { code: "INTERNAL_ERROR", status: 500 },
        response: new Response(null, { status: 500 }),
      });
    await expect(readEveryPage("listRevisions", refused)).rejects.toBeInstanceOf(UnexpectedAnswer);
  });
});
