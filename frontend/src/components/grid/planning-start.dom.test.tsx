// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { example, type FakeClient, fakeClient, type Problem } from "@/test/fixtures";

import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE_ROUTE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}";
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const LABEL = "Structure principale";
const planning = example("nodes_planning") as NodeList;
const ADVANCED = "volume/structure_planning_start_advanced";

/** The planning on the structure of the witness, whose planning starts on 2 March 2026. */
function grid({
  editable = true,
  locale = "fr",
}: { readonly editable?: boolean; readonly locale?: Locale } = {}) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PlanningGrid
        nodes={planning}
        structure={STRUCTURE}
        structureVersion={1}
        planningStart={{ on: "2026-03-02", label: LABEL }}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        editable={editable}
      />
    </NextIntlClientProvider>
  );
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answer: Parameters<typeof fakeClient>[0]): FakeClient {
  const client = fakeClient(answer);
  server.client = client;
  return client;
}

/** The bodies of the writes of the structure the grid sent. */
function written(client: FakeClient) {
  return client.calls.filter((call) => call.route === STRUCTURE_ROUTE).map((call) => call.body);
}

/** Open the form of the date, type a date in it and confirm. */
async function change(date: string) {
  if (screen.queryByRole("form", { name: "Modifier la date de début de planning" }) === null) {
    await userEvent.click(
      screen.getByRole("button", { name: "Modifier la date de début de planning" }),
    );
  }
  const form = screen.getByRole("form", { name: "Modifier la date de début de planning" });
  fireEvent.change(within(form).getByLabelText("Date de début de planning"), {
    target: { value: date },
  });
  await userEvent.click(within(form).getByRole("button", { name: "Confirmer la date" }));
}

beforeEach(() => {
  forgetMessages();
  refresh.mockReset();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the planning start date of the grid of the planning", () => {
  it.each([
    { locale: "fr", said: "02/03/2026" },
    { locale: "en", said: "02/03/2026" },
  ] as const)(
    "presents the date of the structure as the server gives it, in $locale [WF-PLA-0020-A]",
    ({ locale, said }) => {
      serve({});
      render(grid({ locale, editable: false }));
      const region = screen.getByRole("region", {
        name: locale === "fr" ? "Date de début de planning" : "Planning start date",
      });
      expect(region).toHaveTextContent(said);
      expect(within(region).getByText(said)).toHaveAttribute("datetime", "2026-03-02");
      // Read only: the structure does not list `edit_planning`, and no command is offered.
      expect(within(region).queryByRole("button")).toBeNull();
    },
  );

  it("writes the date with the version of the structure read, and shows the date the server answered [WF-PLA-0020-A]", async () => {
    const client = serve({ [STRUCTURE_ROUTE]: ADVANCED });
    render(grid());
    // The week before, as the example of the witness advances it.
    await change("2026-02-23");
    expect(
      await screen.findByText("La date de début de planning est le 23/02/2026."),
    ).toBeVisible();
    expect(written(client)).toEqual([{ planning_start_on: "2026-02-23", lock_version: 1 }]);
    // The page is read anew, for the tasks the server redates; meanwhile the date answered shows.
    expect(refresh).toHaveBeenCalledTimes(1);
    const region = screen.getByRole("region", { name: "Date de début de planning" });
    expect(within(region).getByText("23/02/2026")).toBeInTheDocument();
  });

  it("sends nothing for the date it already bears, and none that is not a date [WF-PLA-0020-A]", async () => {
    const client = serve({ [STRUCTURE_ROUTE]: ADVANCED });
    render(grid());
    await change("2026-03-02");
    await change("");
    expect(written(client)).toEqual([]);
  });

  it("says a day without a working hour, naming the next working day, and writes nothing [WF-PLA-0020-A]", async () => {
    const problem = example("structure_start_non_working_day") as Problem & {
      readonly status: 422;
    };
    const client = serve({ [STRUCTURE_ROUTE]: { problem } });
    render(grid());
    // The Saturday of the example.
    await change("2026-12-19");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /^Les données saisies ne sont pas valides\. Le samedi 19 décembre n’est pas travaillé sur le calendrier de la tâche ; saisis le lundi 21 décembre\./,
    );
    expect(written(client)).toEqual([{ planning_start_on: "2026-12-19", lock_version: 1 }]);
    // Nothing is applied: the date read stays, and the page is not read anew.
    const region = screen.getByRole("region", { name: "Date de début de planning" });
    expect(within(region).getByText("02/03/2026")).toBeInTheDocument();
    expect(refresh).not.toHaveBeenCalled();
  });
});
