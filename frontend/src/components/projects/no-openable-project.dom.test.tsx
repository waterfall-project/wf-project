// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { FUNCTION_GROUPS } from "@/navigation/functions";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { NoOpenableProject, reachableGroups } from "./no-openable-project";

type PermissionCode = components["schemas"]["PermissionCode"];
type ReferenceReadiness = components["schemas"]["ReferenceReadiness"];

const COMPLETE = example("reference_readiness") as ReferenceReadiness;

/** Render in a language, as the shell hands its texts to a screen. */
function inLanguage(children: ReactNode, locale: Locale) {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      {children}
    </NextIntlClientProvider>,
  );
}

describe("the home of an account that opens no project [WF-IHM-0120-A] #2915", () => {
  it("leads to the functions outside any project the account holds, in French, accessibly", async () => {
    const { container } = inLanguage(
      <NoOpenableProject
        permissions={["audit_log.read", "users.read", "portfolio_projects.read"]}
        hasRole
        readiness={COMPLETE}
      />,
      "fr",
    );
    expect(screen.getByRole("heading", { level: 1, name: "Aucun projet à ouvrir" })).toBeVisible();
    const nav = screen.getByRole("navigation", { name: "Fonctions de votre compte" });
    expect(within(nav).getByRole("link", { name: "Journal d’audit" })).toHaveAttribute(
      "href",
      "/admin/audit-log",
    );
    expect(within(nav).getByRole("link", { name: "Portefeuille de projets" })).toHaveAttribute(
      "href",
      "/portfolio/projects",
    );
    await expectAccessible(container);
  });

  it("says that the account has no role yet when it carries none, accessibly", async () => {
    const { container } = inLanguage(
      <NoOpenableProject permissions={[]} hasRole={false} readiness={COMPLETE} />,
      "en",
    );
    expect(screen.getByText(/has no role yet/)).toBeVisible();
    expect(screen.queryByRole("link")).toBeNull();
    await expectAccessible(container);
  });

  it("does not say a role is missing to an account that holds functions of a project only", async () => {
    const { container } = inLanguage(
      <NoOpenableProject permissions={["planning.read"]} hasRole readiness={COMPLETE} />,
      "en",
    );
    expect(
      screen.getByText(/exercised in a project, but it cannot open any project/),
    ).toBeVisible();
    expect(screen.queryByText(/no role yet/)).toBeNull();
    expect(screen.queryByRole("link")).toBeNull();
    await expectAccessible(container);
  });

  it("names the missing prerequisite of the reference data and links it when the account may read it", () => {
    const incomplete = example("reference_readiness_incomplete") as ReferenceReadiness;
    inLanguage(
      <NoOpenableProject permissions={["cost_settings.read"]} hasRole readiness={incomplete} />,
      "en",
    );
    expect(screen.getByRole("heading", { name: "Incomplete reference data" })).toBeVisible();
    expect(screen.getAllByRole("link").map((link) => link.getAttribute("href"))).toContain(
      "/reference/costs",
    );
  });

  it("never leads to a route of a project: no link holds a segment of context", () => {
    const every = FUNCTION_GROUPS.flatMap((group) => group.functions).map(
      (fn) => `${fn.permission}.read` as PermissionCode,
    );
    inLanguage(<NoOpenableProject permissions={every} hasRole readiness={COMPLETE} />, "en");
    const hrefs = screen.getAllByRole("link").map((link) => link.getAttribute("href") ?? "");
    expect(hrefs.length).toBeGreaterThan(0);
    expect(hrefs.filter((href) => href.includes("["))).toEqual([]);
    expect(reachableGroups(every).flatMap((group) => group.functions)).toHaveLength(hrefs.length);
  });
});
