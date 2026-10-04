// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, within } from "@testing-library/react";
import { type ReactNode, Suspense, useEffect } from "react";
import { hydrateRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { SidebarProvider } from "@/components/ui/sidebar";
import { example } from "@/test/fixtures";

import {
  type ShownProject,
  ShownProjectProvider,
  ShowProject,
  useShownProject,
} from "./shown-project";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001",
}));

type Project = components["schemas"]["Project"];

/** Where the page lies in what the server sent: its boundary, not revealed yet. */
const PAGE = "<main>PAGE</main>";

/**
 * The document the server sent: the shell, and within it a page whose boundary is queued, the
 * fallback still in place (`<!--$~-->`), as a screen with a `loading.tsx` stands while React holds
 * back the reveal of what the server streamed.
 */
function sent(shell: (page: ReactNode) => ReactNode): string {
  return renderToStaticMarkup(shell(<main>PAGE</main>)).replace(
    PAGE,
    '<div><!--$~--><template id="B:0"></template><p>Chargement</p><!--/$--></div>',
  );
}

/** The page, as the browser renders it once revealed — or anew, beside the server's. */
function Page() {
  return <h1>Avatar</h1>;
}

let root: Root | undefined;
let container: HTMLElement | undefined;

afterEach(() => {
  act(() => {
    root?.unmount();
  });
  container?.remove();
  vi.restoreAllMocks();
});

/** Hydrate the document the server sent of a shell, its page still pending. */
async function hydratePending(shell: (page: ReactNode) => ReactNode): Promise<HTMLElement> {
  const element = document.createElement("div");
  element.innerHTML = sent(shell);
  document.body.append(element);
  container = element;
  await act(async () => {
    root = hydrateRoot(
      element,
      shell(
        <div>
          <Suspense fallback={<p>Chargement</p>}>
            <Page />
          </Suspense>
        </div>,
      ),
    );
    await Promise.resolve();
  });
  return element;
}

// #173, #180: a context above the page that changes while its boundary is pending makes React
// render the page anew in the browser, beside the one the server sent, which the browser holds.
describe("the shell as the page hydrates", () => {
  it("leaves the page the server sent to hydrate, on a narrow screen the server rendered wide", async () => {
    vi.spyOn(window, "matchMedia").mockImplementation(
      (query) =>
        ({
          matches: true,
          media: query,
          addEventListener: () => undefined,
          removeEventListener: () => undefined,
        }) as unknown as MediaQueryList,
    );
    const page = await hydratePending((inside) => <SidebarProvider>{inside}</SidebarProvider>);
    expect(within(page).queryByRole("heading", { name: "Avatar" })).toBeNull();
    expect(page).toHaveTextContent("Chargement");
  });

  it("leaves the page the server sent to hydrate, when a screen hands its project on to the shell", async () => {
    const project = example("project") as Project;
    const page = await hydratePending((inside) => (
      <ShownProjectProvider>
        <ShowProject project={project} />
        {inside}
      </ShownProjectProvider>
    ));
    expect(within(page).queryByRole("heading", { name: "Avatar" })).toBeNull();
    expect(page).toHaveTextContent("Chargement");
  });
});

/** The label of the project the shell names, as the breadcrumb reads it; each new one told. */
function Named({
  projectId,
  onShown,
}: {
  readonly projectId: string;
  readonly onShown: (shown: ShownProject | undefined) => void;
}) {
  const shown = useShownProject(projectId);
  useEffect(() => {
    onShown(shown);
  }, [shown, onShown]);
  return <p>{shown?.label}</p>;
}

describe("the project a screen hands on", () => {
  it("tells no one when the same project is handed on again, as another screen of it mounts", () => {
    const project = example("project") as Project;
    const told: (ShownProject | undefined)[] = [];
    const tell = (shown: ShownProject | undefined) => {
      told.push(shown);
    };
    const shell = (shown: Project, screen: string) => (
      <ShownProjectProvider>
        <Named projectId={project.project_id} onShown={tell} />
        <ShowProject key={screen} project={shown} />
      </ShownProjectProvider>
    );
    const view = render(shell(project, "project"));
    expect(view.container).toHaveTextContent(project.label);
    expect(told.map((shown) => shown?.label)).toEqual([undefined, project.label]);

    // Another screen of the same project mounts: the project shown is the one already told.
    view.rerender(shell({ ...project }, "revisions"));
    expect(told).toHaveLength(2);

    view.rerender(shell({ ...project, label: "Poste de commande" }, "revisions"));
    expect(view.container).toHaveTextContent("Poste de commande");
    expect(told).toHaveLength(3);
  });
});
