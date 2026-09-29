// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The page of every function of the navigation whose screen is still to come: the route of
 * each exists from the shell on (`functions.json`), and the lot of a screen replaces it by a
 * page of its own — a route written out wins over this one. An address that leads to no
 * function is not found, and neither is one whose project or revision the API does not find
 * — or does not let the user read, which it answers alike (WF-ADM-0110).
 *
 * A function of a project shows the banner of its reading context above it (WF-IHM-0020).
 * Until their screens come (US-0210), the lifecycle of a project shows the commands of the
 * project, and its revisions those of the revision the address names (WF-IHM-0090): not wired
 * to their operations yet, they show what the server offers and what each lacks.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ProjectCommands, RevisionCommands } from "@/components/commands/object-commands";
import { ContextBanner } from "@/components/context/context-banner";
import { type ProjectReading, readAddress } from "@/components/context/reading";
import { ComingSoon } from "@/components/shell/coming-soon";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { findScreen, type NavigationFunction } from "@/navigation/functions";

import { screenMetadata } from "../title";

/** The segments of the address. */
export interface ScreenParams {
  readonly path: readonly string[];
}

/** Title the tab with the function, and with its project when it reads in one. */
export async function generateMetadata({
  params,
}: {
  params: Promise<ScreenParams>;
}): Promise<Metadata> {
  const screen = findScreen((await params).path);
  return screen === undefined ? {} : screenMetadata(screen.fn.label, screen.projectId);
}

/** The commands a function still to come shows already, from the reading of its screen. */
function PlacedCommands({
  fn,
  reading,
}: {
  readonly fn: NavigationFunction;
  readonly reading: ProjectReading | undefined;
}) {
  if (reading === undefined) {
    return null;
  }
  if (fn.permission === "lifecycle") {
    return <ProjectCommands project={reading.project} />;
  }
  if (fn.permission === "revisions" && reading.revision !== undefined) {
    return <RevisionCommands revision={reading.revision} edits={reading.edits} />;
  }
  return null;
}

/** Render the function the address leads to, whose screen is to come. */
export default async function ScreenPage({
  params,
  searchParams,
}: {
  params: Promise<ScreenParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [{ path }, search] = await Promise.all([params, searchParams]);
  const screen = findScreen(path);
  if (screen === undefined) {
    notFound();
  }
  const read =
    screen.projectId === undefined
      ? undefined
      : await readAddress(`/${path.join("/")}`, pageSearch(search));
  if (read === "not_found") {
    notFound();
  }
  return (
    <>
      {read === undefined ? null : <ContextBanner reading={read} />}
      <ComingSoon label={screen.fn.label}>
        <PlacedCommands fn={screen.fn} reading={read} />
      </ComingSoon>
    </>
  );
}
