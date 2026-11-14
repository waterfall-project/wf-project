// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import type { NodeChoice } from "@/components/reference/reference-filters";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { UserList } from "./account-lists";
import type { AccessRole, User } from "./admin-grids";
import { type AuditFilters, authorsOf, readAuditFilters } from "./audit-address";
import { PENDING_DAY } from "@/components/grid/chip-kit";
import { type UserFilters, useUserChips } from "./user-chips";
import { USER_KEPT } from "./user-address";

// The chips of every filter of the table of the accounts, told from the address (#2916): their text,
// the address once each is lifted, and their count on the button of the filters.
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ path: "/admin/users", search: "" }));

vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => page.path,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

const users = example("users") as { items: User[]; meta: Schemas["PaginationMeta"] };
const roles = (example("access_roles") as AccessRole[]).map((role) => ({
  id: role.access_role_id,
  label: role.label,
}));
const nodes: NodeChoice[] = (example("org_nodes") as Schemas["OrgNode"][]).map((node) => ({
  id: node.org_node_id,
  code: node.code,
  label: node.label,
  level: node.level,
}));
const CAMILLE = "01926f3a-7c00-7000-8000-000000000301";
const STRANGER = "01926f3a-7c00-7000-8000-0000000009aa";
const UNKNOWN = "01926f3a-7c00-7000-8000-0000000009ff";

/** The filters an address asks, with the parts the page reads of the server besides it. */
interface Asked {
  readonly origins?: readonly Schemas["UserOrigin"][];
  readonly orgNode?: string;
  readonly accessRoles?: readonly string[];
  readonly active?: boolean;
  readonly named?: AuditFilters["named"];
  /** The accounts offered as authors; those of the page by default. */
  readonly authors?: ReturnType<typeof authorsOf>;
}

/** The table of the accounts, French, the audit filters read from the address. */
function table(asked: Asked = {}) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={USER_KEPT}>
        <UserList
          users={users.items}
          page={users.meta}
          query={{ sort: undefined, search: undefined, size: undefined }}
          preferences={undefined}
          origins={asked.origins ?? []}
          nodes={nodes}
          orgNode={asked.orgNode}
          roles={roles}
          accessRoles={asked.accessRoles ?? []}
          withoutRole={false}
          active={asked.active}
          audit={{ ...readAuditFilters(new URLSearchParams(page.search)), named: asked.named }}
          authors={asked.authors ?? authorsOf(users.items)}
          editable={false}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

const lastAddress = (): unknown => router.push.mock.calls.at(-1)?.[0];

/** Run in a time zone, the process's own given back. */
let zone: string | undefined;
beforeEach(() => {
  zone = process.env.TZ;
  process.env.TZ = "UTC";
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  page.search = "";
});
afterEach(() => {
  if (zone === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = zone;
  }
  vi.restoreAllMocks();
  router.push.mockClear();
});

const NODE = nodes[0] ?? { id: "", code: "", label: "", level: 1 };
const ROLE = roles[0] ?? { id: "", label: "" };

/** The days of the periods: the 1st to the 5th of March, the end excluded as the contract has it. */
const FROM = "2026-03-01T00:00:00.000Z";
const TO = "2026-03-06T00:00:00.000Z";

interface Case {
  readonly name: string;
  /** The address, the filter alone beside a sort the lifting keeps. */
  readonly search: string;
  readonly asked?: Asked;
  /** The heading and the value of the chip. */
  readonly chip: string;
  /** The parameters the lifting removes. */
  readonly lifts: readonly string[];
}

const CASES: readonly Case[] = [
  {
    name: "the origins",
    search: "origins=local%2Cdirectory",
    asked: { origins: ["local", "directory"] },
    chip: "Origine : Créé dans Waterfall, Importé de l’annuaire",
    lifts: ["origins"],
  },
  {
    name: "a node of organisation, by its code and label",
    search: `org_node_id=${NODE.id}`,
    asked: { orgNode: NODE.id },
    chip: `Nœud d’organisation : ${NODE.code} · ${NODE.label}`,
    lifts: ["org_node_id"],
  },
  {
    name: "a node the page does not offer, by its identifier",
    search: `org_node_id=${UNKNOWN}`,
    asked: { orgNode: UNKNOWN },
    chip: `Nœud d’organisation : ${UNKNOWN}`,
    lifts: ["org_node_id"],
  },
  {
    name: "an access role, by its label",
    search: `access_role_ids=${ROLE.id}`,
    asked: { accessRoles: [ROLE.id] },
    chip: `Rôles d’habilitation : ${ROLE.label}`,
    lifts: ["access_role_ids"],
  },
  {
    name: "an access role the session does not read, by its identifier",
    search: `access_role_ids=${UNKNOWN}`,
    asked: { accessRoles: [UNKNOWN] },
    chip: `Rôles d’habilitation : ${UNKNOWN}`,
    lifts: ["access_role_ids"],
  },
  {
    name: "the active accounts, which lifts the old hiding of the deactivated ones too",
    search: "is_active=true&include_inactive=false",
    asked: { active: true },
    chip: "État du compte : Actif",
    lifts: ["is_active", "include_inactive"],
  },
  {
    name: "the deactivated accounts",
    search: "is_active=false",
    asked: { active: false },
    chip: "État du compte : Désactivé",
    lifts: ["is_active"],
  },
  ...(["created", "updated"] as const).flatMap((column): Case[] => {
    const heading = column === "created" ? "Créé le" : "Modifié le";
    return [
      {
        name: `the ${column} period between two days`,
        search: `${column}_at_from=${FROM}&${column}_at_to=${TO}`,
        chip: `${heading} : du 1 mars 2026 au 5 mars 2026`,
        lifts: [`${column}_at_from`, `${column}_at_to`],
      },
      {
        name: `the ${column} period since a day`,
        search: `${column}_at_from=${FROM}`,
        chip: `${heading} : depuis le 1 mars 2026`,
        lifts: [`${column}_at_from`],
      },
      {
        name: `the ${column} period until a day, the end excluded`,
        search: `${column}_at_to=${TO}`,
        chip: `${heading} : jusqu’au 5 mars 2026`,
        lifts: [`${column}_at_to`],
      },
    ];
  }),
  ...(["created", "updated"] as const).flatMap((column): Case[] => {
    const heading = column === "created" ? "Créé par" : "Modifié par";
    const user = `${column}_by_user_id`;
    const kind = `${column}_by_kind`;
    return [
      {
        name: `the ${column} author, an account the page offers`,
        search: `${user}=${CAMILLE}`,
        chip: `${heading} : Camille Martin`,
        lifts: [user, kind],
      },
      {
        name: `the ${column} author, an account the page does not offer, read by its names`,
        search: `${user}=${STRANGER}`,
        asked: {
          authors: [],
          named: [{ user_id: STRANGER, first_name: "Sacha", last_name: "Lemaire" }],
        },
        chip: `${heading} : Sacha Lemaire`,
        lifts: [user, kind],
      },
      {
        name: `the ${column} author, an account nobody names`,
        search: `${user}=${STRANGER}`,
        asked: { authors: [] },
        chip: `${heading} : Un compte`,
        lifts: [user, kind],
      },
      {
        name: `the ${column} author, the platform`,
        search: `${kind}=platform`,
        chip: `${heading} : La plateforme`,
        lifts: [user, kind],
      },
      {
        name: `the ${column} author, any account`,
        search: `${kind}=user`,
        chip: `${heading} : Un compte`,
        lifts: [user, kind],
      },
    ];
  }),
];

describe("the chips of the filters of the accounts", () => {
  it.each(CASES)(
    "tell $name, and lift it by the parameters of the address that say it [WF-IHM-0130-A]",
    async ({ search, asked, chip, lifts }) => {
      page.search = `sort_by=email&${search}`;
      render(table(asked));
      const cross = screen.getByRole("button", { name: `Retirer le filtre ${chip}` });
      expect(cross.closest("li")).toHaveTextContent(chip);
      // Whatever parameters the filter writes, the lifting removes them all and the sort stays.
      await userEvent.click(cross);
      const lifted = new URLSearchParams(page.search);
      for (const name of lifts) {
        lifted.delete(name);
      }
      const rest = lifted.toString();
      expect(lastAddress()).toBe(`/admin/users?${rest}`);
      expect(rest).toBe("sort_by=email");
    },
  );

  it("are as many as the button of the filters counts, with every filter on [WF-IHM-0130-A]", () => {
    page.search = [
      "origins=local",
      `org_node_id=${NODE.id}`,
      `access_role_ids=${ROLE.id}`,
      "is_active=true",
      `created_at_from=${FROM}`,
      `updated_at_to=${TO}`,
      `created_by_user_id=${CAMILLE}`,
      "updated_by_kind=platform",
    ].join("&");
    render(
      table({
        origins: ["local"],
        orgNode: NODE.id,
        accessRoles: [ROLE.id],
        active: true,
      }),
    );
    const chips = screen.getByRole("list", { name: "Filtres actifs" });
    expect(chips.children).toHaveLength(8);
    expect(screen.getByRole("button", { name: "Filtres (8)" })).toBeVisible();
  });

  it("clear a parameter the reading set aside too: « Effacer les filtres » leaves nothing of the filters in the address [WF-IHM-0130-A] (#2916)", async () => {
    page.search = "origins=nope&is_active=true&search=a";
    render(table({ active: true }));
    await userEvent.click(screen.getByRole("button", { name: "Effacer les filtres" }));
    // The search is no filter: it stays; the origin the contract would refuse goes with the others.
    expect(lastAddress()).toBe("/admin/users?search=a");
  });

  it("tell the hiding of the deactivated accounts of an old address, `include_inactive` alone, as the active accounts, and lift it [WF-ADM-0060-A] (#2916)", async () => {
    page.search = "include_inactive=false&sort_by=email";
    render(table({ active: true }));
    expect(screen.getByRole("list", { name: "Filtres actifs" })).toHaveTextContent(
      "État du compte : Actif",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Retirer le filtre État du compte : Actif" }),
    );
    expect(lastAddress()).toBe("/admin/users?sort_by=email");
  });

  it("tell nothing of `include_inactive=true`, which every account satisfies [WF-ADM-0060-A] (#2916)", () => {
    page.search = "include_inactive=true";
    render(table());
    expect(screen.queryByRole("list", { name: "Filtres actifs" })).toBeNull();
  });

  it("leave the focus where it is when a chip lifted changes nothing of the address, the chips going later [WF-IHM-0130-A] (#2916)", async () => {
    // The chip told by the props and not by the address: lifting it asks no navigation that would arrive.
    page.search = "";
    const { rerender } = render(table({ active: true }));
    await userEvent.click(
      screen.getByRole("button", { name: "Retirer le filtre État du compte : Actif" }),
    );
    rerender(table());
    expect(screen.getByRole("button", { name: /^Filtres/ })).not.toHaveFocus();
  });

  it("tell a period in the local days of the workstation, whatever its time zone [WF-IHM-0130-A]", () => {
    // Midnight of the 1st to midnight of the 6th at Auckland (UTC+13 in March): the days are the 1st
    // to the 5th there, though the instants fall on the 28th of February and the 5th in UTC.
    process.env.TZ = "Pacific/Auckland";
    page.search = "created_at_from=2026-02-28T11:00:00.000Z&created_at_to=2026-03-05T11:00:00.000Z";
    render(table());
    expect(screen.getByText("Créé le : du 1 mars 2026 au 5 mars 2026")).toBeVisible();
  });
});

describe("the chips of a period before the browser", () => {
  /** Tell the chips of an address as the server renders them: no day is told before the browser. */
  function Told({ filters }: { readonly filters: UserFilters }) {
    return useUserChips(filters, [], []).map((chip) => <p key={chip.key}>{chip.value}</p>);
  }

  it("tell no day, whose zone the server does not know, and the end of a period excluded names the next day [WF-IHM-0130-A]", () => {
    const filters: UserFilters = {
      origins: [],
      orgNode: undefined,
      accessRoles: [],
      withoutRole: false,
      active: undefined,
      audit: readAuditFilters(new URLSearchParams(`created_at_to=${TO}`)),
      authors: [],
    };
    const html = renderToStaticMarkup(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <Told filters={filters} />
      </NextIntlClientProvider>,
    );
    expect(html).toBe(`<p>jusqu’au ${PENDING_DAY}</p>`);
    expect(html).not.toContain("2026-03-06");
    expect(html).not.toContain("6 mars 2026");
  });
});
