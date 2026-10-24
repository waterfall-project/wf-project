// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of the timelines as a document renders the tree its page composes: what the page
 * hands the frieze for its exported image — the timeline, the project, the revision, and the date
 * the dates were calculated at, which the answer carries (`meta.scheduled_at`, #1404).
 */
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChartOption } from "@/components/chart/chart";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import { example, type FakeAnswers, fakeClient } from "@/test/fixtures";

import TimelinesPage from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));
/** What the instance out of the screen was handed for the exported image. */
const canvas = vi.hoisted(() => ({ options: [] as unknown[] }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));
// The image is drawn on a canvas, which the simulated document does not paint: an instance in its
// place records what it is asked to draw.
vi.mock("echarts/core", async (actual) => {
  const echarts = await actual<typeof import("echarts/core")>();
  return {
    ...echarts,
    init: (...args: Parameters<typeof echarts.init>) => {
      if (args[2]?.renderer !== "canvas") {
        return echarts.init(...args);
      }
      return {
        setOption: (option: unknown) => canvas.options.push(option),
        getDataURL: () => "data:image/png;base64,iVBORw0KGgo=",
        dispose: () => undefined,
      };
    },
  };
});

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";

beforeEach(() => {
  canvas.options = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    [NODES]: "nodes_timeline",
    "GET /projects/{project_id}/timelines": "timelines",
  };
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1000);
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the exported image of the timeline shown", () => {
  // aucune exigence : propre à l'US (US-0530, la provenance câblée de la page à la frise).
  it("is titled by the timeline and the project, and says the revision and the date its dates were calculated at, read from the answer", async () => {
    const timelines = example("timelines") as { label: string }[];
    const project = example("project") as { label: string };
    const revision = example("revision") as { version_name?: string | null };
    const meta = (example("nodes_timeline") as { meta: { scheduled_at: string } }).meta;
    const read = await TimelinesPage({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
      searchParams: Promise.resolve({}),
    });
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        {read}
      </NextIntlClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Exporter en PNG" }));
    expect(canvas.options).toHaveLength(1);
    const { title } = canvas.options[0] as ChartOption;
    // The revision as its version name, or as the current one, the example giving it none.
    const named = revision.version_name ?? "Révision en cours";
    expect(title).toMatchObject({
      text: `${timelines[0]?.label ?? ""} — ${project.label}`,
      subtext: `Révision : ${named} · Calculé le ${formatTimestamp(meta.scheduled_at, "fr")}`,
    });
  });
});
