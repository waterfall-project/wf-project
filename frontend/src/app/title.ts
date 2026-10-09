// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The title of the tab of a page: the screen, and the project it reads in when there is one,
 * so that two tabs of two projects tell each other apart.
 */
import "server-only";

import type { Metadata } from "next";
import { createTranslator } from "next-intl";

import { readProject } from "@/components/context/reading";
import { CATALOGUES } from "@/i18n/catalogues";
import { requestLanguage } from "@/i18n/request";
import type { AccountEntry } from "@/navigation/account";
import type { NavigationFunction } from "@/navigation/functions";

/** What a title names: a function, the list of projects, or a page of the account. */
export type ScreenLabel =
  NavigationFunction["label"] | "functionGroups.projects" | AccountEntry["label"];

/**
 * The label of a project, or `undefined` when it cannot be read — read once for the request,
 * with the page and the banner of its context.
 */
async function projectLabel(projectId: string): Promise<string | undefined> {
  const answer = await readProject(projectId);
  return answer?.data?.label;
}

/**
 * The metadata of a page: the title of its screen, in the language of the request, with the
 * label of its project when it reads in one the API lets the user read.
 */
export async function screenMetadata(label: ScreenLabel, projectId?: string): Promise<Metadata> {
  const { locale } = await requestLanguage();
  const t = createTranslator({ locale, messages: CATALOGUES[locale] });
  const screen = t(label);
  const project = projectId === undefined ? undefined : await projectLabel(projectId);
  return {
    title:
      project === undefined
        ? t("app.title", { screen })
        : t("app.projectTitle", { screen, project }),
  };
}
