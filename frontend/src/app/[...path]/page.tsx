// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The page of every function of the navigation whose screen is still to come: the route of
 * each exists from the shell on (`functions.json`), and the lot of a screen replaces it by a
 * page of its own — a route written out wins over this one. An address that leads to no
 * function is not found, and neither is one whose project or revision the API does not find
 * — or does not let the user read, which it answers alike (WF-ADM-0110): the same screen
 * (`not-found.tsx`). The API out of reach is announced by the screen of failure
 * (`error.tsx`).
 *
 * A function of a project shows the banner of its reading context above it (WF-IHM-0020).
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ContextBanner } from "@/components/context/context-banner";
import { readAddress } from "@/components/context/reading";
import { ComingSoon } from "@/components/shell/coming-soon";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { findScreen } from "@/navigation/functions";

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
      <ComingSoon
        label={screen.fn.label}
        icon={FUNCTION_ICONS[screen.fn.permission]}
        density={FUNCTION_DENSITY[screen.fn.permission]}
      />
    </>
  );
}
