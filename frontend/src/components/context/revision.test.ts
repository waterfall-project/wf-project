// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { BASE_PARAMETER } from "@/navigation/context";

import { baseHref, baseOptions, listedRevision, revisionHref } from "./revision";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const CURRENT = "01926f3a-7c00-7000-8000-000000000102";
const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
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

  it("keeps the base of an active comparison for any other revision chosen [WF-IHM-0020-A]", () => {
    // Toute autre révision choisie garde la base (décision de l'auteur du 2026-11-15).
    const query = new URLSearchParams({ [BASE_PARAMETER]: OFFER, subproject_id: SUBPROJECT });
    const planning = (revision: string) => `/projects/${PROJECT}/revisions/${revision}/planning`;
    expect(revisionHref(planning(CURRENT), query, REFERENCE)).toBe(
      `${planning(REFERENCE)}?subproject_id=${SUBPROJECT}&${BASE_PARAMETER}=${OFFER}`,
    );
  });

  it("lifts the comparison when the base itself is chosen for revision read [WF-IHM-0020-A]", () => {
    // Choisir pour révision lue la base d'une comparaison active lève la comparaison (US-2330).
    const query = new URLSearchParams({ [BASE_PARAMETER]: REFERENCE, subproject_id: SUBPROJECT });
    expect(
      revisionHref(`/projects/${PROJECT}/revisions/${CURRENT}/estimate`, query, REFERENCE),
    ).toBe(`/projects/${PROJECT}/revisions/${REFERENCE}/estimate?subproject_id=${SUBPROJECT}`);
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
      status: "draft",
      is_reference: false,
    });
  });
});

describe("the bases the banner offers", () => {
  const listed = (name: "revisions" | "revisions_marked") =>
    (example(name) as { items: Revision[] }).items.map(listedRevision);
  const offered = (revisions: ReturnType<typeof listed>, read: Revision) =>
    baseOptions(revisions, read).map((revision) => revision.revision_id);

  it("are the marked revisions of the project but the one read, never the revision under way [WF-IHM-0020-A]", () => {
    // Le bandeau offre pour base les révisions marquées du projet, hors la révision lue (#3176).
    expect(offered(listed("revisions"), example("revision") as Revision)).toEqual([
      REFERENCE,
      OFFER,
    ]);
    expect(offered(listed("revisions_marked"), example("revision_marked") as Revision)).toEqual([
      OFFER,
    ]);
    expect(offered(listed("revisions"), example("revision_offer") as Revision)).toEqual([
      REFERENCE,
    ]);
  });

  it("come the revision read is a copy of first, then the reference, then the others in the order of the server", () => {
    // The current revision, as if it were a copy of the offer rather than of the reference: a
    // variant of the witness, its source alone changed.
    const ofTheOffer = { ...(example("revision") as Revision), source_revision_id: OFFER };
    expect(offered(listed("revisions"), ofTheOffer)).toEqual([OFFER, REFERENCE]);
  });

  it("are chosen in the address, the rest of it kept, and lifted from it", () => {
    const query = new URLSearchParams({ sort_by: "label", subproject_id: SUBPROJECT });
    const remaining = `/projects/${PROJECT}/revisions/${CURRENT}/remaining`;
    expect(baseHref(remaining, query, REFERENCE)).toBe(
      `${remaining}?sort_by=label&subproject_id=${SUBPROJECT}&${BASE_PARAMETER}=${REFERENCE}`,
    );
    query.set(BASE_PARAMETER, REFERENCE);
    expect(baseHref(remaining, query, undefined)).toBe(
      `${remaining}?sort_by=label&subproject_id=${SUBPROJECT}`,
    );
  });
});
