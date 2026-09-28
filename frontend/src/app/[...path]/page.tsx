// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The page of every function of the navigation whose screen is still to come: the route of
 * each exists from the shell on (`functions.json`), and the lot of a screen replaces it by a
 * page of its own — a route written out wins over this one. An address that leads to no
 * function is not found.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ComingSoon } from "@/components/shell/coming-soon";
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
export default async function ScreenPage({ params }: { params: Promise<ScreenParams> }) {
  const screen = findScreen((await params).path);
  if (screen === undefined) {
    notFound();
  }
  return <ComingSoon label={screen.fn.label} />;
}
