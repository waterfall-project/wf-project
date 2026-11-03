// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OutcomeNotice } from "@/components/commands/outcome-notice";
import {
  forgetMessages,
  MESSAGES_KEY,
  noteMessage,
  readMessages,
} from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type Problem } from "@/test/fixtures";
import { tasksRegion } from "@/test/task-panel";

import { OWNER_KEY } from "./session-end";
import { STORAGE_KEY } from "./storage";
import { TaskPanel, TasksButton, TaskTracker } from "./task-tracker";

// The router of Next, as far as a notice needs it.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/account",
  useSearchParams: () => new URLSearchParams(),
}));

const ALIX = "01926f3a-7c00-7000-8000-000000000011";
const BEA = "01926f3a-7c00-7000-8000-000000000012";
const MARKING = "01926f3a-7c00-7000-8000-000000000931";
const LEFT = "Marquage de la révision V2 demandé.";

/** The tracker of the shell, for an account, around a page. */
function shell(accountId: string | undefined, page: ReactNode = null) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <TaskTracker signedIn={accountId !== undefined} accountId={accountId}>
        <TasksButton />
        <TaskPanel />
        {page}
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** What a session left in the tab: a task still followed and a message in the history. */
function leave(owner: string | undefined) {
  window.sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify([
      { key: MARKING, task_id: MARKING, kind: "revision_mark", status: "running", subject: "V2" },
    ]),
  );
  noteMessage({}, { tone: "success", sentence: LEFT });
  if (owner !== undefined) {
    window.sessionStorage.setItem(OWNER_KEY, owner);
  }
}

/** The sentences of the history of the messages, as it stands. */
function told() {
  return readMessages().messages.map((message) => message.sentence);
}

beforeEach(() => {
  window.sessionStorage.clear();
  forgetMessages();
});

describe("what a session leaves in the tab for the next (#1180)", () => {
  it.each([
    ["another account", BEA],
    ["no account kept", undefined],
  ] as const)(
    "wipes the tasks followed and the history of the messages that %s wrote, and keeps the account that reads",
    (_, owner) => {
      leave(owner);
      render(shell(ALIX));
      expect(told()).toEqual([]);
      expect(window.sessionStorage.getItem(MESSAGES_KEY)).toBeNull();
      expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
      expect(within(tasksRegion()).queryAllByRole("listitem")).toHaveLength(0);
      expect(window.sessionStorage.getItem(OWNER_KEY)).toBe(ALIX);
    },
  );

  it("keeps them for the account that wrote them: a reload is no end of session", () => {
    leave(ALIX);
    render(shell(ALIX));
    expect(told()).toEqual([LEFT]);
    expect(within(tasksRegion()).getAllByRole("listitem")).toHaveLength(1);
    expect(window.sessionStorage.getItem(OWNER_KEY)).toBe(ALIX);
  });

  it("wipes them when a session found ended offers the sign-in, even to the account that wrote them", () => {
    leave(ALIX);
    const problem = example("session_expired") as Problem;
    const { rerender } = render(shell(ALIX));
    expect(told()).toEqual([LEFT]);
    rerender(
      shell(
        ALIX,
        <OutcomeNotice
          outcome={{ kind: "signed_out", problem, conflictingObjectId: null }}
          onClear={vi.fn()}
        />,
      ),
    );
    expect(screen.getByRole("link", { name: "Se connecter" })).toBeVisible();
    // Only the sentence that tells the session over stays; what the session wrote, and whose it was,
    // are gone from the tab, for whoever signs in next.
    expect(told()).not.toContain(LEFT);
    expect(window.sessionStorage.getItem(MESSAGES_KEY)).not.toContain(LEFT);
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(window.sessionStorage.getItem(OWNER_KEY)).toBeNull();
  });

  it("wipes nothing for a refusal that leaves the session standing", () => {
    leave(ALIX);
    const problem = example("session_expired") as Problem;
    render(
      shell(
        ALIX,
        <OutcomeNotice
          outcome={{
            kind: "refused",
            problem: { ...problem, status: 403 },
            conflictingObjectId: null,
          }}
          onClear={vi.fn()}
        />,
      ),
    );
    expect(told()).toContain(LEFT);
    expect(window.sessionStorage.getItem(STORAGE_KEY)).not.toBeNull();
  });

  it("offers the sign-in outside the tracker as well", () => {
    const problem = example("session_expired") as Problem;
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <OutcomeNotice
          outcome={{ kind: "signed_out", problem, conflictingObjectId: null }}
          onClear={vi.fn()}
        />
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("link", { name: "Se connecter" })).toBeVisible();
  });
});
