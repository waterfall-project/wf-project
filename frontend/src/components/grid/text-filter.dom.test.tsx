// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { TextFilter } from "./text-filter";

// The server of Next, as far as the filter needs it: the address it reads and the navigations it
// asks.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(page.search),
}));

/** The parameter the filter of the code of the nodes writes. */
const CODE = "org_code";

/**
 * The filter of the code of the nodes, under the address that filters on a code, on its own: it keeps
 * the address last asked itself, outside of a screen that shares one.
 */
function filter(value: string | undefined) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TextFilter name={CODE} label="Code du nœud" value={value} length={20} />
    </NextIntlClientProvider>
  );
}

/** The field of the code. */
function field(): HTMLElement {
  return screen.getByRole("searchbox", { name: "Code du nœud" });
}

/** The address of the last navigation the filter asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

beforeEach(() => {
  page.search = "";
});

afterEach(() => {
  router.push.mockReset();
});

describe("the filter of a list on a text", () => {
  it("filters the tree on the code entered, lifted when emptied [WF-IHM-0130-A]", async () => {
    page.search = "org_search=BE";
    render(filter(undefined));
    expect(field()).toHaveAttribute("maxlength", "20");
    await userEvent.type(field(), " ELEC {Enter}");
    expect(lastAddress()).toBe("/reference/resources?org_search=BE&org_code=ELEC");
    await userEvent.clear(field());
    await userEvent.type(field(), "{Enter}");
    expect(lastAddress()).toBe("/reference/resources?org_search=BE");
  });

  it("sets the code anew when the address changes it, back in the history, what was typed and not sent given up", async () => {
    page.search = "org_code=ELEC";
    const { rerender } = render(filter("ELEC"));
    expect(field()).toHaveValue("ELEC");
    await userEvent.type(field(), "-TRIC");
    expect(field()).toHaveValue("ELEC-TRIC");
    // Back to an address that filtered on another code, then on none.
    page.search = "org_code=BE";
    rerender(filter("BE"));
    expect(field()).toHaveValue("BE");
    page.search = "";
    rerender(filter(undefined));
    expect(field()).toHaveValue("");
    expect(router.push).not.toHaveBeenCalled();
  });

  it("keeps the focus in the field that sent the code once the address arrives", async () => {
    const { rerender } = render(filter(undefined));
    const sent = field();
    await userEvent.type(sent, "ELEC{Enter}");
    expect(lastAddress()).toBe("/reference/resources?org_code=ELEC");
    // The address sent arrives: the field stays, with the focus and the code (#537).
    page.search = "org_code=ELEC";
    rerender(filter("ELEC"));
    expect(field()).toBe(sent);
    expect(sent).toHaveFocus();
    expect(sent).toHaveValue("ELEC");
    // Back in the history to the address the code was typed over: it shows no code, the entry
    // given up.
    page.search = "";
    rerender(filter(undefined));
    expect(sent).toHaveValue("");
  });

  it("keeps what was typed on while the code sent was on its way, once it arrives (#557)", async () => {
    const { rerender } = render(filter(undefined));
    await userEvent.type(field(), "ELEC{Enter}");
    // Typed on before the server answers.
    await userEvent.type(field(), "-TRIC");
    page.search = "org_code=ELEC";
    rerender(filter("ELEC"));
    expect(field()).toHaveValue("ELEC-TRIC");
    expect(field()).toHaveFocus();
    // Sent in turn, it goes on from the address shown.
    await userEvent.type(field(), "{Enter}");
    expect(lastAddress()).toBe("/reference/resources?org_code=ELEC-TRIC");
  });

  it("shows a code sent on while the one before was on its way as the address writes it, once it arrives (#557)", async () => {
    const { rerender } = render(filter(undefined));
    await userEvent.type(field(), "ELEC{Enter}");
    // Typed on and sent before the server answers: the second code arrives in the place of the first.
    await userEvent.type(field(), "-TRIC  {Enter}");
    expect(lastAddress()).toBe("/reference/resources?org_code=ELEC-TRIC");
    page.search = "org_code=ELEC-TRIC";
    rerender(filter("ELEC-TRIC"));
    expect(field()).toHaveValue("ELEC-TRIC");
  });

  it("forgets what was typed on while the code sent was on its way when « Précédent » comes before it (#557)", async () => {
    page.search = "org_code=BE";
    const { rerender } = render(filter("BE"));
    await userEvent.clear(field());
    await userEvent.type(field(), "ELEC{Enter}");
    await userEvent.type(field(), "-TRIC");
    // « Précédent » before the server answers, to an address of no code.
    page.search = "";
    rerender(filter(undefined));
    expect(field()).toHaveValue("");
  });

  it("never brings back by « Suivant » a code typed over the address « Précédent » came back to (#557)", async () => {
    const { rerender } = render(filter(undefined));
    await userEvent.type(field(), "ELEC{Enter}");
    page.search = "org_code=ELEC";
    rerender(filter("ELEC"));
    // « Précédent », a code typed and given up, then « Suivant » to the address the code sent
    // brought: it shows its own code.
    page.search = "";
    rerender(filter(undefined));
    await userEvent.type(field(), "ZZZ");
    page.search = "org_code=ELEC";
    rerender(filter("ELEC"));
    expect(field()).toHaveValue("ELEC");
  });
});
