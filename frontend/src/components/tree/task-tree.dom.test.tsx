// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { NodeList } from "@/components/grid/nodes";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { summaryTree } from "./summaries";
import { TaskTree } from "./task-tree";

// The summaries of the core of the witness, down to the second level.
const core = (example("nodes_core") as NodeList).items.filter((node) => node.kind === "task");
const PROJECT = "Modernisation du poste de commande";

/** Render the tree of the core at a depth. */
function renderTree(depth = 2) {
  return render(
    <TaskTree name="Arborescence" project={PROJECT} nodes={summaryTree(core, depth)} />,
  );
}

/** An item of the tree, by the start of its name. */
function item(name: RegExp): HTMLElement {
  return screen.getByRole("treeitem", { name });
}

describe("the task tree drawn", () => {
  it("is a tree under the root of the project: the first level side by side, the next under its parent [WF-PLA-0110-A]", () => {
    renderTree();
    const tree = screen.getByRole("tree", { name: "Arborescence" });
    const root = within(tree).getAllByRole("treeitem")[0];
    expect(root).toHaveAttribute("aria-level", "1");
    expect(root?.textContent).toMatch(new RegExp(`^${PROJECT}`));
    const lot = item(/^8 Poste de commande/);
    expect(lot).toHaveAttribute("aria-level", "2");
    expect(lot).toHaveAttribute("aria-expanded", "true");
    expect(within(lot).getByRole("treeitem")).toHaveAttribute("aria-level", "3");
    expect(item(/^1 Études/)).not.toHaveAttribute("aria-expanded");
    // The first level is laid side by side, the deeper ones down.
    expect(lot.parentElement).toHaveClass("flex");
    expect(within(lot).getByRole("group")).not.toHaveClass("flex");
  });

  it("is one stop of the tabulation, whose arrows go through the items as in any tree, and change nothing", async () => {
    renderTree();
    await userEvent.tab();
    const root = screen.getAllByRole("treeitem")[0];
    expect(root).toHaveFocus();
    expect(root).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowRight}");
    expect(item(/^1 Études/)).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(item(/^8 Poste/)).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    expect(item(/^13 Risque/)).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(item(/^8 Poste/)).toHaveFocus();
    await userEvent.keyboard("{End}");
    expect(item(/^19 Installation/)).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}");
    expect(item(/^13 Risque/)).toHaveFocus();
    await userEvent.keyboard("{Home}");
    expect(root).toHaveFocus();
    // Only one item is in the tabulation; no key opens an entry.
    await userEvent.keyboard("{Enter}x");
    expect(screen.getAllByRole("treeitem").filter((each) => each.tabIndex === 0)).toEqual([root]);
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("is the root alone for a plan without a summary", () => {
    render(<TaskTree name="Arborescence" project={PROJECT} nodes={[]} />);
    expect(screen.getAllByRole("treeitem")).toHaveLength(1);
    expect(screen.queryByRole("group")).toBeNull();
  });

  it("is accessible", async () => {
    const { container } = renderTree(1);
    await expectAccessible(container);
  });
});
