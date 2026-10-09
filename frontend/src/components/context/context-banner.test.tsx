// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { readContext } from "@/navigation/context";
import { example } from "@/test/fixtures";

import { ContextBanner } from "./context-banner";
import type { Project } from "./reading";

// What the banner hands the shell, as the component that takes it on receives it.
const handed = vi.hoisted((): unknown[] => []);

vi.mock("@/components/shell/shown-project", () => ({
  ShowProject: ({ project }: { project: unknown }) => {
    handed.push(project);
    return null;
  },
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";

describe("the banner of the reading context", () => {
  it("hands the shell only what it shows of the project: its identifier, label, code and state", () => {
    const pathname = `/projects/${PROJECT}/lifecycle`;
    const context = readContext(pathname, new URLSearchParams());
    if (context === undefined) {
      throw new Error("no context");
    }
    const project = example("project") as Project;
    renderToStaticMarkup(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <ContextBanner
          reading={{
            pathname,
            context,
            project,
            revision: undefined,
            edits: new Set(),
            readOnly: false,
            filters: [],
          }}
        />
      </NextIntlClientProvider>,
    );
    expect(handed).toEqual([
      {
        project_id: project.project_id,
        label: "Modernisation du poste de commande",
        code: "PRJ-001",
        state: "in_progress",
      },
    ]);
  });
});
