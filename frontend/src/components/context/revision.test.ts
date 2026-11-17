// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { listedRevision, revisionHref } from "./revision";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const CURRENT = "01926f3a-7c00-7000-8000-000000000102";
const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const STRUCTURE = "01926f3a-7c00-7000-8000-000000000203";

type Revision = components["schemas"]["Revision"];

describe("the address of a revision chosen", () => {
  it("opens the same screen on the revision chosen, the sub-project filtered and the date of calculation kept [WF-IHM-0020-A]", () => {
    // La révision choisie s'ouvre sur le même écran, le sous-projet filtré et la date de calcul
    // conservés (US-2330).
    const query = new URLSearchParams({ subproject_id: SUBPROJECT, as_of: "2026-05-31" });
    expect(
      revisionHref(`/projects/${PROJECT}/revisions/${CURRENT}/indicators`, query, REFERENCE),
    ).toBe(
      `/projects/${PROJECT}/revisions/${REFERENCE}/indicators?subproject_id=${SUBPROJECT}&as_of=2026-05-31`,
    );
  });

  it("leaves what names a part of the revision left: its structure, a sort, a search, a page", () => {
    const query = new URLSearchParams({
      structure: STRUCTURE,
      sort_by: "label",
      search: "Revue",
      offset: "50",
      subproject_id: SUBPROJECT,
    });
    expect(
      revisionHref(`/projects/${PROJECT}/revisions/${CURRENT}/planning`, query, REFERENCE),
    ).toBe(`/projects/${PROJECT}/revisions/${REFERENCE}/planning?subproject_id=${SUBPROJECT}`);
  });

  it("names the revision as a parameter on a function of the project itself", () => {
    const query = new URLSearchParams({ revision_id: CURRENT, from: REFERENCE });
    expect(revisionHref(`/projects/${PROJECT}/revisions`, query, REFERENCE)).toBe(
      `/projects/${PROJECT}/revisions?revision_id=${REFERENCE}`,
    );
  });

  it("opens the revision itself from its own path", () => {
    expect(
      revisionHref(`/projects/${PROJECT}/revisions/${CURRENT}`, new URLSearchParams(), REFERENCE),
    ).toBe(`/projects/${PROJECT}/revisions/${REFERENCE}`);
  });

  it("is the path itself on an address that is no screen of a project", () => {
    expect(revisionHref("/system", new URLSearchParams(), REFERENCE)).toBe("/system");
  });
});

describe("a revision as the banner offers it", () => {
  it("keeps of a revision of the contract what the banner names, nothing more", () => {
    const [current] = (example("revisions") as { items: Revision[] }).items;
    expect(current && listedRevision(current)).toEqual({
      revision_id: CURRENT,
      version_name: null,
      is_reference: false,
    });
  });
});
