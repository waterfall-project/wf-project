// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  contextCookie,
  contextQuery,
  LAST_CONTEXT_COOKIE,
  readContext,
  rememberedAddress,
} from "./context";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000401";
const REMAINING = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;

describe("the reading context", () => {
  it("reads the project and the revision in the path, the filters in the parameters", () => {
    const search = new URLSearchParams({ as_of: "2026-05-31", subproject_id: SUBPROJECT, q: "x" });
    const context = readContext(REMAINING, search);
    expect(context?.projectId).toBe(PROJECT);
    expect(context?.revisionId).toBe(REVISION);
    // In the order of the contract's names, the parameters of other purposes left out.
    expect(context && contextQuery(context)).toBe(`?subproject_id=${SUBPROJECT}&as_of=2026-05-31`);
  });

  it("reads a project without a revision, and without filters", () => {
    const context = readContext(`/projects/${PROJECT}`, new URLSearchParams("subproject_id="));
    expect(context).toEqual({
      projectId: PROJECT,
      revisionId: undefined,
      parameters: new URLSearchParams(),
    });
    expect(context && contextQuery(context)).toBe("");
  });

  it.each(["/", "/projects", "/portfolio/projects", "/system", "/projects/"])(
    "reads no project in %s",
    (pathname) => {
      expect(readContext(pathname, new URLSearchParams())).toBeUndefined();
    },
  );

  it("keeps the address of a context in a cookie of the whole front", () => {
    const address = `${REMAINING}?subproject_id=${SUBPROJECT}`;
    expect(contextCookie(address)).toBe(
      `${LAST_CONTEXT_COOKIE}=${encodeURIComponent(address)}; path=/; max-age=31536000; samesite=lax`,
    );
  });

  it("leads back from the cookie to a project only, with its context alone", () => {
    const address = `${REMAINING}?subproject_id=${SUBPROJECT}&as_of=2026-05-31`;
    expect(rememberedAddress(address)).toBe(address);
    expect(rememberedAddress(`${REMAINING}?sort_by=label&as_of=2026-05-31`)).toBe(
      `${REMAINING}?as_of=2026-05-31`,
    );
    expect(rememberedAddress(`/projects/${PROJECT}`)).toBe(`/projects/${PROJECT}`);
    expect(rememberedAddress("https://elsewhere.example/projects/1")).toBeUndefined();
    expect(rememberedAddress("//elsewhere.example/projects/1")).toBeUndefined();
    expect(rememberedAddress("/admin/users")).toBeUndefined();
    expect(rememberedAddress(undefined)).toBeUndefined();
  });
});
