// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of a project itself share — the project, its settings, its lifecycle: the
 * parameters of their route, the context their address holds, and the reading of it, not found
 * alike for an address that names no project and for a project the API does not find — or does
 * not let the user read, which it answers alike (WF-ADM-0110).
 */
import "server-only";

import { notFound } from "next/navigation";

import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import {
  type PageSearchParams,
  pageSearch,
  type ProjectContext,
  readContext,
} from "@/navigation/context";

/** The route parameters of a project. */
export interface ProjectParams {
  readonly projectId: string;
}

/** What Next hands a page of a project. */
export interface ProjectPageProps {
  readonly params: Promise<ProjectParams>;
  readonly searchParams: Promise<PageSearchParams>;
}

/** The path of a screen of a project, and the context its address holds. */
export interface ProjectAddress {
  readonly projectId: string;
  readonly pathname: string;
  readonly context: ProjectContext;
}

/**
 * The address of the screen of a project — the project itself, or one of its functions —, or
 * not found before the API is asked anything when it names no project.
 */
export async function projectAddress(
  { params, searchParams }: ProjectPageProps,
  screen?: string,
): Promise<ProjectAddress> {
  const [{ projectId }, search] = await Promise.all([params, searchParams]);
  const pathname = `/projects/${projectId}${screen === undefined ? "" : `/${screen}`}`;
  const context = readContext(pathname, pageSearch(search));
  if (context === undefined) {
    notFound();
  }
  return { projectId, pathname, context };
}

/** The reading of a screen of a project, which its banner shows; not found as the others. */
export async function readProjectScreen(address: ProjectAddress): Promise<ProjectReading> {
  const read = await readProjectContext(address.pathname, address.context);
  if (read === "not_found") {
    notFound();
  }
  return read;
}
