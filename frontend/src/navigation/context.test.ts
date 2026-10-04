// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  contextAddress,
  contextCookie,
  contextQuery,
  LAST_CONTEXT_COOKIE,
  pageSearch,
  readContext,
  rememberedAddress,
  withoutFilter,
} from "./context";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const REMAINING = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
const LIFECYCLE = `/projects/${PROJECT}/lifecycle`;

describe("the reading context", () => {
  it("reads the project and the revision in the path, the filters in the parameters", () => {
    const search = new URLSearchParams({ as_of: "2026-05-31", subproject_id: SUBPROJECT, q: "x" });
    const context = readContext(REMAINING, search);
    expect(context?.projectId).toBe(PROJECT);
    expect(context?.revisionId).toBe(REVISION);
    expect(context?.revisionInPath).toBe(true);
    // In the order of the contract's names, the parameters of other purposes left out.
    expect(context && contextQuery(context, false)).toBe(
      `?subproject_id=${SUBPROJECT}&as_of=2026-05-31`,
    );
  });

  it("reads the revision a function of the project itself carries as a parameter", () => {
    const search = new URLSearchParams({ revision_id: REVISION, as_of: "2026-05-31" });
    const context = readContext(LIFECYCLE, search);
    expect(context?.revisionId).toBe(REVISION);
    expect(context?.revisionInPath).toBe(false);
    expect(context && contextAddress(LIFECYCLE, context)).toBe(
      `${LIFECYCLE}?revision_id=${REVISION}&as_of=2026-05-31`,
    );
  });

  it("reads the exchanges of a project as a screen of the project itself", () => {
    const exchanges = `/projects/${PROJECT}/exchanges`;
    const context = readContext(exchanges, new URLSearchParams({ revision_id: REVISION }));
    expect(context?.revisionId).toBe(REVISION);
    expect(context?.revisionInPath).toBe(false);
    const under = `/projects/${PROJECT}/revisions/${REVISION}/exchanges`;
    expect(readContext(under, new URLSearchParams())).toBeUndefined();
  });

  it("reads a project without a revision, and without filters", () => {
    const context = readContext(`/projects/${PROJECT}`, new URLSearchParams("subproject_id="));
    expect(context).toEqual({
      projectId: PROJECT,
      revisionId: undefined,
      revisionInPath: false,
      parameters: new URLSearchParams(),
    });
    expect(context && contextQuery(context, true)).toBe("");
  });

  it.each([
    "/",
    "/projects",
    "/portfolio/projects",
    "/system",
    "/projects/",
    `/projects/${PROJECT}/unknown`,
    `/projects/${PROJECT}/planning`,
    `/projects/${PROJECT}/revisions/${REVISION}/lifecycle`,
    `/projects/${PROJECT}/revisions/${REVISION}/risks/more`,
    "/projects/../admin",
    "/projects/%2e%2e/revisions",
  ])("reads no project in %s", (pathname) => {
    expect(readContext(pathname, new URLSearchParams())).toBeUndefined();
  });

  it("keeps the address of a context in a cookie of the whole front", () => {
    const address = `${REMAINING}?subproject_id=${SUBPROJECT}`;
    expect(contextCookie(address)).toBe(
      `${LAST_CONTEXT_COOKIE}=${encodeURIComponent(address)}; path=/; max-age=31536000; samesite=lax`,
    );
  });

  it("leads back from the cookie to a screen of a project only, with its context alone", () => {
    const address = `${REMAINING}?subproject_id=${SUBPROJECT}&as_of=2026-05-31`;
    expect(rememberedAddress(address)).toBe(address);
    expect(rememberedAddress(`${REMAINING}?sort_by=label&as_of=2026-05-31`)).toBe(
      `${REMAINING}?as_of=2026-05-31`,
    );
    // The revision in the path wins over a parameter, which is then dropped.
    expect(rememberedAddress(`${REMAINING}?revision_id=other`)).toBe(REMAINING);
    expect(rememberedAddress(`${LIFECYCLE}?revision_id=${REVISION}`)).toBe(
      `${LIFECYCLE}?revision_id=${REVISION}`,
    );
    expect(rememberedAddress(`${LIFECYCLE}?revision_id=../x`)).toBe(LIFECYCLE);
    expect(rememberedAddress(`/projects/${PROJECT}`)).toBe(`/projects/${PROJECT}`);
  });

  it.each([
    "https://elsewhere.example/projects/1",
    "//elsewhere.example/projects/1",
    "/projects/..//evil.example",
    `/projects/${PROJECT}/revisions/${REVISION}/../../../admin/users`,
    `/projects/${PROJECT}//evil.example`,
    "/admin/users",
    undefined,
  ])("leads nowhere from the cookie %j", (value) => {
    expect(rememberedAddress(value)).toBeUndefined();
  });

  it("lifts one filter, and keeps the revision and the other filter", () => {
    const search = new URLSearchParams({ subproject_id: SUBPROJECT, as_of: "2026-05-31" });
    const inRevision = readContext(REMAINING, search);
    expect(inRevision && withoutFilter(REMAINING, inRevision, "as_of")).toBe(
      `${REMAINING}?subproject_id=${SUBPROJECT}`,
    );
    search.set("revision_id", REVISION);
    const inProject = readContext(LIFECYCLE, search);
    expect(inProject && withoutFilter(LIFECYCLE, inProject, "subproject_id")).toBe(
      `${LIFECYCLE}?revision_id=${REVISION}&as_of=2026-05-31`,
    );
    // The context read is left as it was.
    expect(inProject?.parameters.get("subproject_id")).toBe(SUBPROJECT);
  });

  it("reads the search parameters of a page as those of the browser, a repeated one once", () => {
    const search = pageSearch({ as_of: "2026-05-31", subproject_id: [SUBPROJECT, "unassigned"] });
    expect(search.get("as_of")).toBe("2026-05-31");
    expect(search.get("subproject_id")).toBe(SUBPROJECT);
    expect(search.get("revision_id")).toBeNull();
    expect(search.get("toString")).toBeNull();
    expect(pageSearch({ as_of: [] }).get("as_of")).toBeNull();
  });
});
