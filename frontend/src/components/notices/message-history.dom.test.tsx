// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";

import { DoneNotice } from "./done-notice";
import {
  forgetMessages,
  isScreen,
  markMessagesSeen,
  MESSAGES_KEPT,
  MESSAGES_KEY,
  noteMessage,
  readMessages,
  unreadRefusals,
} from "./message-history";
import { MessageList } from "./message-list";
import { type Say, useSaid } from "./said";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => SCREEN,
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/planning`;
const LOT = "01926f3a-7c00-7000-8000-000000000301";

/** In French. */
function french(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {children}
    </NextIntlClientProvider>
  );
}

/** A refusal of the API, naming the object in conflict. */
const TAKEN: Outcome<unknown> = {
  kind: "refused",
  problem: { code: "ALREADY_EXISTS", status: 409 },
  conflictingObjectId: LOT,
};

/** The unexpected error of the service, with the correlation identifier of its request. */
const UNEXPECTED: Outcome<unknown> = {
  kind: "refused",
  problem: { code: "INTERNAL_ERROR", status: 500, correlation_id: "req-7f3a9c" },
  conflictingObjectId: null,
};

/** The messages of the history as the panel lists them, the last first. */
function listed(): HTMLElement[] {
  return within(screen.getByRole("region", { name: "Messages" })).queryAllByRole("listitem");
}

beforeEach(() => {
  window.sessionStorage.clear();
  forgetMessages();
  window.history.replaceState(null, "", SCREEN);
});

afterEach(() => {
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});

describe("the history of the messages", () => {
  it("notes the refusal a notice tells once, however often it renders it, with the object in conflict", () => {
    const view = render(
      french(<OutcomeNotice outcome={TAKEN} names={{ [LOT]: "Lot A" }} onClear={vi.fn()} />),
    );
    view.rerender(
      french(<OutcomeNotice outcome={TAKEN} names={{ [LOT]: "Lot A" }} onClear={vi.fn()} />),
    );
    const { messages } = readMessages();
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatchObject({
      id: 1,
      tone: "refusal",
      sentence: "Cet élément existe déjà.",
      object: "Lot A",
      screen: { href: SCREEN },
    });
    // The notice is the one alert: the history announces nothing.
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });

  it("notes the object the screen gives before the one in conflict, and the reference of an unexpected error", () => {
    render(french(<OutcomeNotice outcome={UNEXPECTED} subject="Devis" onClear={vi.fn()} />));
    expect(readMessages().messages[0]).toMatchObject({
      tone: "refusal",
      sentence: "Erreur inattendue du service.",
      object: "Devis",
      reference: "req-7f3a9c",
    });
  });

  it("notes nothing of a success a notice does not tell, nor before any outcome", () => {
    render(
      french(
        <>
          <OutcomeNotice outcome={undefined} onClear={vi.fn()} />
          <OutcomeNotice outcome={{ kind: "done", data: null }} onClear={vi.fn()} />
          <DoneNotice title={undefined} of={undefined} />
        </>,
      ),
    );
    expect(readMessages().messages).toEqual([]);
  });

  it("notes the success a confirmation says, once for each outcome it tells", () => {
    const first = { kind: "done" };
    const view = render(french(<DoneNotice title="Préférences enregistrées." of={first} />));
    view.rerender(french(<DoneNotice title="Préférences enregistrées." of={first} />));
    view.rerender(french(<DoneNotice title="Préférences enregistrées." of={{ kind: "done" }} />));
    expect(readMessages().messages.map(({ tone, sentence }) => [tone, sentence])).toEqual([
      ["success", "Préférences enregistrées."],
      ["success", "Préférences enregistrées."],
    ]);
  });

  it("counts the refusals not seen yet, until the panel shows them", () => {
    noteMessage({}, { tone: "refusal", sentence: "Refusé." });
    noteMessage({}, { tone: "success", sentence: "Fait." });
    noteMessage({}, { tone: "refusal", sentence: "Refusé encore." });
    expect(unreadRefusals(readMessages())).toBe(2);
    markMessagesSeen();
    expect(unreadRefusals(readMessages())).toBe(0);
    noteMessage({}, { tone: "refusal", sentence: "Refusé enfin." });
    expect(unreadRefusals(readMessages())).toBe(1);
  });

  it("keeps the last messages only", () => {
    for (let rank = 1; rank <= MESSAGES_KEPT + 2; rank += 1) {
      noteMessage({}, { tone: "success", sentence: String(rank) });
    }
    const { messages } = readMessages();
    expect(messages).toHaveLength(MESSAGES_KEPT);
    expect(messages[0]?.sentence).toBe("3");
    expect(messages.at(-1)?.id).toBe(MESSAGES_KEPT + 2);
  });

  it("keeps the history in the storage of the tab, read back after a reload, what is not a message left", async () => {
    noteMessage({}, { tone: "refusal", sentence: "Refusé.", reference: "req-1" });
    const kept = JSON.parse(window.sessionStorage.getItem(MESSAGES_KEY) ?? "null") as {
      messages: object[];
      seen: number;
    };
    window.sessionStorage.setItem(
      MESSAGES_KEY,
      JSON.stringify({
        messages: [
          ...kept.messages,
          { id: 2, tone: "loud" },
          null,
          { ...kept.messages[0], screen: { href: "https://elsewhere.example" } },
        ],
        seen: 0,
      }),
    );
    // A reload of the tab: the module is read anew.
    vi.resetModules();
    const reloaded = await import("./message-history");
    expect(reloaded.readMessages().messages).toEqual([
      expect.objectContaining({ id: 1, sentence: "Refusé.", reference: "req-1" }),
    ]);
    expect(reloaded.unreadRefusals(reloaded.readMessages())).toBe(1);
    window.sessionStorage.setItem(MESSAGES_KEY, "{not json");
    vi.resetModules();
    expect((await import("./message-history")).readMessages().messages).toEqual([]);
  });

  it("goes on in the page when the browser refuses the storage", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("refused", "QuotaExceededError");
    });
    noteMessage({}, { tone: "success", sentence: "Fait." });
    expect(readMessages().messages).toHaveLength(1);
  });

  it("lists the messages the last first, each with its tone in words, its time and a link back to its screen, and marks them seen", async () => {
    noteMessage(
      {},
      { tone: "success", sentence: "Fait.", screen: { href: SCREEN, project: "Tour Horizon" } },
    );
    noteMessage(
      {},
      { tone: "refusal", sentence: "Refusé.", detail: "Pour cause.", reference: "req-2" },
    );
    noteMessage({}, { tone: "success", sentence: "Ailleurs.", screen: { href: "/nowhere" } });
    const follow = vi.fn();
    const { container } = render(french(<MessageList onFollow={follow} />));
    const [elsewhere, refused, done] = listed();
    expect(elsewhere).toHaveTextContent("Ailleurs.");
    expect(within(elsewhere ?? document.body).getByRole("link")).toHaveTextContent(
      "Écran d’origine",
    );
    expect(refused).toHaveTextContent(/^Refus\s:Refusé\.Pour cause\.Référence\s: req-2/);
    expect(done).toHaveTextContent(/^Réussite\s:Fait\./);
    const back = within(done ?? document.body).getByRole("link", {
      name: "Planification — Tour Horizon",
    });
    expect(back).toHaveAttribute("href", SCREEN);
    expect(done?.querySelector("time")).toHaveAttribute("datetime");
    expect(unreadRefusals(readMessages())).toBe(0);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
    await expectAccessible(container);
  });

  it("says the session has no message yet", () => {
    render(french(<MessageList onFollow={vi.fn()} />));
    expect(listed()).toEqual([]);
    expect(screen.getByText("Aucun message dans cette session.")).toBeVisible();
  });
});

describe("the screens the history keeps", () => {
  it.each([
    "//elsewhere.example/projects",
    "/\\elsewhere.example",
    "https://elsewhere.example",
    "projects",
  ])("keeps no address of another site, or none of the application: %s", (href) => {
    expect(isScreen({ href })).toBe(false);
  });

  it("keeps an address of the application, with the project it showed", () => {
    expect(isScreen({ href: `${SCREEN}?sort=label`, project: "Tramway" })).toBe(true);
  });
});

describe("a status said by hand (useSaid)", () => {
  /** A screen that says in its status what its commands did, and hands its way of saying over. */
  function Saying({ onSay }: { readonly onSay: (say: Say) => void }) {
    const [said, say] = useSaid();
    onSay(say);
    return (
      <p role="status">{said === undefined ? null : <span key={said.count}>{said.text}</span>}</p>
    );
  }

  it("says what a command did, and notes it in the history with the object it is about [WF-IHM-0080-A]", () => {
    let say: Say = () => undefined;
    render(<Saying onSay={(given) => (say = given)} />);
    act(() => {
      say("« Lot A » enregistré.", { object: "Lot A" });
    });
    expect(screen.getByRole("status")).toHaveTextContent("« Lot A » enregistré.");
    act(() => {
      say("« Lot A » enregistré.", { object: "Lot A" });
    });
    // The same text said twice is two outcomes, noted twice.
    expect(readMessages().messages).toEqual([
      expect.objectContaining({
        tone: "success",
        sentence: "« Lot A » enregistré.",
        object: "Lot A",
      }),
      expect.objectContaining({ id: 2, sentence: "« Lot A » enregistré." }),
    ]);
  });

  it("notes nothing of what an unavailable command pressed lacks: nothing was sent", () => {
    let say: Say = () => undefined;
    render(<Saying onSay={(given) => (say = given)} />);
    act(() => {
      say("Désactiver : il faut une révision en cours.", { noted: false });
    });
    expect(screen.getByRole("status")).toHaveTextContent("Désactiver");
    expect(readMessages().messages).toEqual([]);
  });
});
