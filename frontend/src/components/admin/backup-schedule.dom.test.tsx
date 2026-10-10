// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
  type Problem,
} from "@/test/fixtures";

import { BackupScheduleSection } from "./backup-schedule";

type Schemas = components["schemas"];

// The server of Next, as far as the form needs it: the fake back, and the page rendered again once
// the schedule is set.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// The tests of a location, counted once each has its answer: what a test waits for before it says
// that an answer fell.
const settled = vi.hoisted(() => ({ tests: 0 }));
// A write of the schedule whose server action rejects once `until` settles — the API out of reach,
// as `fetch` rejects in the browser —; none, and the action asks the fake back.
const failing = vi.hoisted((): { until: Promise<void> | undefined } => ({ until: undefined }));
vi.mock("@/api/actions/backups", async (original) => {
  const actual = await original<typeof import("@/api/actions/backups")>();
  return {
    ...actual,
    setBackupSchedule: async (...asked: Parameters<typeof actual.setBackupSchedule>) => {
      if (failing.until === undefined) {
        return actual.setBackupSchedule(...asked);
      }
      await failing.until;
      throw new TypeError("Failed to fetch");
    },
    testExternalBackupLocation: async (
      ...asked: Parameters<typeof actual.testExternalBackupLocation>
    ) => {
      try {
        return await actual.testExternalBackupLocation(...asked);
      } finally {
        settled.tests += 1;
      }
    },
  };
});
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/backups",
  useSearchParams: () => new URLSearchParams(),
}));

const SET = "PUT /backup-schedule";
const TEST = "POST /external-backup-locations/{location_name}/test";
const witness = example("backup_schedule") as Schemas["BackupSchedule"];
const weekly = example("backup_schedule_weekly") as Schemas["BackupSchedule"];
const disabled = example("backup_schedule_disabled") as Schemas["BackupSchedule"];
const locations = example("external_backup_locations") as Schemas["ExternalBackupLocation"][];

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(
    { [SET]: "backup_schedule_set", [TEST]: "external_backup_location_tested", ...answers },
    timing,
  );
  server.client = client;
  return client;
}

/** A part of the screen, in French. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

/** Open the form of the schedule, and give it back. */
async function openForm(
  schedule = witness,
  declared: readonly Schemas["ExternalBackupLocation"][] = locations,
): Promise<HTMLElement> {
  render(inFrench(<BackupScheduleSection schedule={schedule} locations={declared} />));
  await userEvent.click(screen.getByRole("button", { name: "Modifier la planification" }));
  return screen.getByRole("dialog", { name: "Modifier la planification" });
}

/** Save the form. */
async function save(form: HTMLElement) {
  await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
}

/** Hold every call of the fake back until the function given back is called. */
function held(): { readonly timing: FakeTiming; readonly release: () => void } {
  const settles: (() => void)[] = [];
  const until = new Promise<void>((settle) => {
    settles.push(settle);
  });
  return {
    timing: { hold: () => until },
    release: () => {
      for (const settle of settles) {
        settle();
      }
    },
  };
}

/** What the section of the schedule last said beside its command. */
function said(): HTMLElement {
  return within(screen.getByLabelText("Planification")).getByRole("status");
}

/** Type a count in a field of the form, in place of what it held. */
async function retype(form: HTMLElement, name: string, typed: string) {
  const field = within(form).getByRole("textbox", { name });
  await userEvent.clear(field);
  await userEvent.type(field, typed);
  return field;
}

/**
 * A text of the catalogue as a description is compared: whole, each space standing for the plain or
 * the no-break one French writes before a colon and inside quotation marks.
 */
function spaced(text: string): RegExp {
  const literal = text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`^${literal.replace(/ /g, "\\s")}$`);
}

const zone = process.env.TZ;

beforeEach(() => {
  // The workstation in Paris, its local time two hours ahead of universal time in June.
  process.env.TZ = "Europe/Paris";
});

afterEach(() => {
  vi.useRealTimers();
  if (zone === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = zone;
  }
  refresh.mockClear();
  router.refresh.mockClear();
  settled.tests = 0;
  failing.until = undefined;
});

describe("the schedule of the backups", () => {
  it("offers no form to a session that may not modify the backups: the schedule is read alone", () => {
    serve();
    render(inFrench(<BackupScheduleSection schedule={witness} locations={undefined} />));
    expect(screen.getByLabelText("Planification")).toHaveTextContent("Rétention7 sauvegardes");
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("sets the schedule whole from the version read, shows the answer in place of the reading, and reads the page anew", async () => {
    const client = serve();
    const form = await openForm();
    await retype(form, "Sauvegardes conservées", "14");
    await save(form);
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // Everything read is sent back, the copy kept, with the version the form opened on.
    expect(client.calls.map(({ route, body }) => ({ route, body }))).toEqual([
      { route: SET, body: { ...witness, retained_count: 14 } },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(
      screen.getAllByRole("status").find((region) => region.textContent !== ""),
    ).toHaveTextContent("Planification enregistrée.");
    expect(screen.getByLabelText("Planification")).toHaveTextContent(
      "Rétention14 sauvegardes conservées",
    );
    expect(screen.getByRole("button", { name: "Modifier la planification" })).toHaveFocus();
  });

  it("enters the time in universal time, the local time it stands for said beside it, for a daily schedule the time alone", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-06-03T14:05:00Z"));
    serve();
    const form = await openForm();
    const time = within(form).getByLabelText("Heure (UTC)");
    expect(time).toHaveValue("01:00");
    expect(time).toHaveAccessibleDescription(spaced("Soit 03:00 à l’heure de ce poste."));
    fireEvent.change(time, { target: { value: "23:30" } });
    expect(time).toHaveAccessibleDescription(spaced("Soit 01:30 à l’heure de ce poste."));
  });

  it("names for a weekly schedule the local day its universal day and time fall on, the day before west of Greenwich", async () => {
    // Sunday at 02:30 in universal time is Saturday at 19:30 in Los Angeles in June.
    process.env.TZ = "America/Los_Angeles";
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-06-03T14:05:00Z"));
    serve();
    const form = await openForm(weekly, []);
    expect(within(form).getByLabelText("Heure (UTC)")).toHaveAccessibleDescription(
      spaced("Soit samedi 19:30 à l’heure de ce poste."),
    );
  });

  it.each([
    ["Saturday at 20:00", "6", "20:00", "dimanche 01:30"],
    ["Sunday at 18:45", "7", "18:45", "lundi 00:15"],
  ] as const)(
    "names for a weekly schedule the local day after its universal day east of Greenwich, half an hour off: %s",
    async (_time, day, time, local) => {
      // Kolkata is five hours and a half ahead of universal time, all year long.
      process.env.TZ = "Asia/Kolkata";
      vi.useFakeTimers({ toFake: ["Date"] });
      vi.setSystemTime(new Date("2026-06-03T14:05:00Z"));
      serve();
      const form = await openForm(weekly, []);
      await userEvent.selectOptions(within(form).getByLabelText("Jour"), day);
      const at = within(form).getByLabelText("Heure (UTC)");
      fireEvent.change(at, { target: { value: time } });
      expect(at).toHaveAccessibleDescription(spaced(`Soit ${local} à l’heure de ce poste.`));
    },
  );

  it.each([
    ["suspended", disabled],
    ["on", witness],
  ] as const)(
    "refuses before asking anything a time half entered on a schedule %s, rather than sending none",
    async (_state, schedule) => {
      // A time control half entered gives an empty text, which it says is no time (`badInput`).
      const client = serve();
      const form = await openForm(schedule);
      const time = within(form).getByLabelText("Heure (UTC)");
      Object.defineProperty(time, "validity", { value: { badInput: true }, configurable: true });
      fireEvent.change(time, { target: { value: "" } });
      await save(form);
      expect(time).toHaveFocus();
      expect(time).toHaveAttribute("aria-invalid", "true");
      expect(time).toHaveAccessibleDescription(spaced("Une heure, au format HH:MM."));
      expect(client.calls).toEqual([]);
    },
  );

  it("requires the frequency and the time of a schedule on alone, and says so: a suspended one is sent without them", async () => {
    const client = serve();
    const form = await openForm();
    const frequency = within(form).getByLabelText("Fréquence");
    const time = within(form).getByLabelText("Heure (UTC)");
    expect(frequency).toHaveAttribute("aria-required", "true");
    expect(time).toHaveAttribute("aria-required", "true");
    await userEvent.selectOptions(frequency, "");
    fireEvent.change(time, { target: { value: "" } });
    await save(form);
    expect(frequency).toHaveFocus();
    for (const field of [frequency, time]) {
      expect(field).toHaveAttribute("aria-invalid", "true");
      expect(field).toHaveAccessibleDescription(/Une valeur est requise\.$/);
    }
    expect(client.calls).toEqual([]);
    await userEvent.selectOptions(within(form).getByLabelText("État"), "Suspendue");
    expect(frequency).not.toHaveAttribute("aria-required");
    expect(time).not.toHaveAttribute("aria-required");
    await save(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).not.toHaveProperty("frequency");
    expect(client.calls[0]?.body).toEqual({
      is_enabled: false,
      weekday: null,
      retained_count: 7,
      external_copy: witness.external_copy,
      lock_version: witness.lock_version,
    });
  });

  it("sets a weekly schedule on its day, without a copy once « no copy » is chosen", async () => {
    const client = serve();
    const form = await openForm();
    await userEvent.selectOptions(within(form).getByLabelText("Fréquence"), "Hebdomadaire");
    await userEvent.selectOptions(within(form).getByLabelText("Jour"), "Dimanche");
    fireEvent.change(within(form).getByLabelText("Heure (UTC)"), { target: { value: "02:30" } });
    await userEvent.selectOptions(
      within(form).getByLabelText("Copie externe vers"),
      "Aucune copie",
    );
    await save(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    const body = client.calls[0]?.body;
    expect(body).not.toHaveProperty("external_copy");
    expect(body).toEqual({
      is_enabled: true,
      retained_count: witness.retained_count,
      lock_version: witness.lock_version,
      frequency: "weekly",
      weekday: 7,
      at_time: "02:30",
    });
  });

  it("refuses before asking anything a weekly schedule without its day, the day taking the focus", async () => {
    const client = serve();
    const form = await openForm();
    const day = within(form).getByLabelText("Jour");
    expect(day).not.toHaveAttribute("aria-required");
    await userEvent.selectOptions(within(form).getByLabelText("Fréquence"), "Hebdomadaire");
    expect(day).toHaveAttribute("aria-required", "true");
    await save(form);
    expect(day).toHaveFocus();
    expect(day).toHaveAttribute("aria-invalid", "true");
    expect(day).toHaveAccessibleDescription(
      spaced("Pour une sauvegarde hebdomadaire seulement. Une valeur est requise."),
    );
    expect(client.calls).toEqual([]);
  });

  it("refuses before asking anything fewer copies outside the platform than backups on it, the least named at the field", async () => {
    // Le corps de WF-EXP-0050 : « Les sauvegardes sont conservées hors de la plateforme selon une
    // rétention au moins égale à celle configurée sur la plateforme. »
    const client = serve();
    const form = await openForm();
    await retype(form, "Sauvegardes conservées", "40");
    await save(form);
    const copies = within(form).getByRole("textbox", { name: "Copies gardées" });
    expect(copies).toHaveFocus();
    expect(copies).toHaveAccessibleDescription(
      spaced(
        "Au moins autant que les sauvegardes conservées. La valeur sort des limites admises. Valeur minimale : 40.",
      ),
    );
    expect(client.calls).toEqual([]);
  });

  it("requires the folder and the count of a copy once a location is chosen, and says so; « no copy » withdraws it", async () => {
    const client = serve();
    const form = await openForm();
    const path = within(form).getByRole("textbox", { name: "Dossier dans l’emplacement" });
    const copies = within(form).getByRole("textbox", { name: "Copies gardées" });
    await userEvent.clear(path);
    await userEvent.clear(copies);
    for (const field of [path, copies]) {
      expect(field).toHaveAttribute("aria-required", "true");
    }
    await save(form);
    expect(path).toHaveFocus();
    for (const field of [path, copies]) {
      expect(field).toHaveAttribute("aria-invalid", "true");
      expect(field).toHaveAccessibleDescription(/Une valeur est requise\.$/);
    }
    expect(client.calls).toEqual([]);
    await userEvent.selectOptions(
      within(form).getByLabelText("Copie externe vers"),
      "Aucune copie",
    );
    for (const field of [path, copies]) {
      expect(field).not.toHaveAttribute("aria-required");
    }
    await save(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).not.toHaveProperty("external_copy");
  });

  it("says in one sending a field left empty and a rule a field breaks: a location undeclared and no folder", async () => {
    // The witness schedule copies to « secours-lyon », which the installation here no longer declares.
    const client = serve();
    const form = await openForm(witness, locations.slice(0, 1));
    const path = within(form).getByRole("textbox", { name: "Dossier dans l’emplacement" });
    await userEvent.clear(path);
    await save(form);
    // The field's own refusal and the rule's, both said at once, the first in the form focused.
    const location = within(form).getByLabelText("Copie externe vers");
    expect(location).toHaveFocus();
    expect(location).toHaveAccessibleDescription(
      spaced("Emplacement externe inconnu de l’installation."),
    );
    expect(path).toHaveAccessibleDescription(/Une valeur est requise\.$/);
    expect(client.calls).toEqual([]);
  });

  it.each([
    ["-3", "2"],
    ["0", "2"],
    ["366", "30"],
  ])(
    "leaves to the server the count of copies of a retention out of its bounds, %s, which it refuses by its own: %s copies sent",
    async (retention, count) => {
      const client = serve();
      const form = await openForm();
      await retype(form, "Sauvegardes conservées", retention);
      const copies = await retype(form, "Copies gardées", count);
      await save(form);
      await vi.waitFor(() => {
        expect(client.calls).toHaveLength(1);
      });
      expect(copies).not.toHaveAttribute("aria-invalid");
      expect(client.calls[0]?.body).toMatchObject({
        retained_count: Number(retention),
        external_copy: { retained_count: Number(count) },
      });
    },
  );

  it("refuses before asking anything a count that is no whole number, saying what it takes; its bounds are the server's", async () => {
    const client = serve();
    const form = await openForm();
    const retained = await retype(form, "Sauvegardes conservées", "7,5");
    const copies = await retype(form, "Copies gardées", "3,5");
    await save(form);
    expect(retained).toHaveAccessibleDescription(spaced("Un nombre entier de sauvegardes."));
    expect(copies).toHaveAccessibleDescription(
      spaced("Au moins autant que les sauvegardes conservées. Un nombre entier de copies."),
    );
    // A whole number below zero is one: what it lacks is its bound, the least the copies keep.
    await retype(form, "Sauvegardes conservées", "7");
    await retype(form, "Copies gardées", "-30");
    await save(form);
    expect(copies).toHaveAccessibleDescription(
      spaced(
        "Au moins autant que les sauvegardes conservées. La valeur sort des limites admises. Valeur minimale : 7.",
      ),
    );
    expect(client.calls).toEqual([]);
  });

  it.each([
    [
      "backup_schedule_unknown_location",
      "Copie externe vers",
      `${locations[1]?.description ?? ""} `,
      "Emplacement externe inconnu de l’installation.",
    ],
    [
      "backup_schedule_path_invalid",
      "Dossier dans l’emplacement",
      "Un chemin relatif, sans « / » en tête ni « .. ». ",
      "Chemin invalide : il doit être relatif, sans « .. ».",
    ],
    [
      "backup_schedule_retention_too_short",
      "Copies gardées",
      "Au moins autant que les sauvegardes conservées. ",
      "La valeur sort des limites admises. Valeur minimale : 7.",
    ],
  ] as const)(
    "says at its field the copy the server refuses (%s), the form open to correct it",
    async (refusal, field, note, said) => {
      serve({ [SET]: { problem: example(refusal) as Problem & { status: 422 } } });
      const form = await openForm();
      await save(form);
      const control = within(form).getByLabelText(field);
      await vi.waitFor(() => {
        expect(control).toHaveFocus();
      });
      expect(control).toHaveAttribute("aria-invalid", "true");
      expect(control).toHaveAccessibleDescription(spaced(`${note}${said}`));
      expect(within(form).queryByRole("alert")).toBeNull();
      expect(refresh).not.toHaveBeenCalled();
    },
  );

  it("says the version stale under the form, and offers to read the page anew", async () => {
    serve({
      [SET]: {
        problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 3 } },
      },
    });
    const form = await openForm();
    await save(form);
    await userEvent.click(await within(form).findByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("offers the locations the installation declares, by name and kind, and no copy where it declares none", async () => {
    serve();
    const form = await openForm();
    const location = within(form).getByLabelText("Copie externe vers");
    expect(
      within(location)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual([
      "Aucune copie",
      "nas-siege (Partage réseau monté)",
      "secours-lyon (Compartiment S3)",
    ]);
    // What the installation says of the location chosen, never a secret nor an address.
    expect(location).toHaveAccessibleDescription(
      spaced(
        "Compartiment S3 du site de secours de Lyon, hors du centre de données de la plateforme.",
      ),
    );
    await expectAccessible(document.body);
  });

  it("keeps offered by its name a location the schedule sets and the installation no longer declares, refused at its field before anything is asked, and offers no test of it", async () => {
    // The witness schedule copies to « secours-lyon »; the installation here declares « nas-siege »
    // alone. The copy is not withdrawn unsaid: the form says the location unknown at its field.
    const client = serve();
    const form = await openForm(witness, locations.slice(0, 1));
    const location = within(form).getByLabelText("Copie externe vers");
    expect(location).toHaveValue("secours-lyon");
    expect(within(location).getByRole("option", { selected: true })).toHaveTextContent(
      "secours-lyon (non déclaré par l’installation)",
    );
    expect(within(form).queryByRole("button", { name: "Tester l’emplacement" })).toBeNull();
    await save(form);
    expect(location).toHaveFocus();
    expect(location).toHaveAccessibleDescription(
      spaced("Emplacement externe inconnu de l’installation."),
    );
    expect(client.calls).toEqual([]);
  });

  it("keeps its command inactive while a write of the dialog closed is under way, shows its answer, then opens on the version it brings (#661, #678)", async () => {
    const { timing, release } = held();
    const client = serve({}, timing);
    const form = await openForm();
    await save(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    // The focus back on the command, which says why it waits.
    const command = screen.getByRole("button", { name: "Modifier la planification" });
    expect(command).toHaveFocus();
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAttribute("aria-busy", "true");
    expect(command).toHaveAccessibleDescription("Enregistrement en cours…");
    await userEvent.click(command);
    expect(screen.queryByRole("dialog")).toBeNull();
    release();
    await vi.waitFor(() => {
      expect(said()).toHaveTextContent("Planification enregistrée.");
    });
    expect(command).not.toHaveAccessibleDescription();
    expect(screen.getByLabelText("Planification")).toHaveTextContent(
      "Rétention14 sauvegardes conservées",
    );
    expect(command).not.toHaveAttribute("aria-disabled");
    await userEvent.click(command);
    await save(screen.getByRole("dialog", { name: "Modifier la planification" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    expect(client.calls[1]?.body).toMatchObject({ retained_count: 14, lock_version: 3 });
  });

  it("tells above the schedule a refusal answered once the dialog is gone", async () => {
    const { timing, release } = held();
    const client = serve(
      { [SET]: { problem: example("backup_schedule_path_invalid") as Problem & { status: 422 } } },
      timing,
    );
    const form = await openForm();
    await save(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    const command = screen.getByRole("button", { name: "Modifier la planification" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    release();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Les données saisies ne sont pas valides.",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    // Refused, the write no longer holds the command.
    expect(command).not.toHaveAttribute("aria-disabled");
    await userEvent.click(command);
    expect(screen.getByRole("dialog", { name: "Modifier la planification" })).toBeVisible();
  });

  it("frees its command once a write of the dialog closed is rejected, the API out of reach, and says so above the schedule", async () => {
    const settles: (() => void)[] = [];
    failing.until = new Promise<void>((settle) => {
      settles.push(settle);
    });
    serve();
    const form = await openForm();
    await save(form);
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    const command = screen.getByRole("button", { name: "Modifier la planification" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    for (const settle of settles) {
      settle();
    }
    expect(await screen.findByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(command).not.toHaveAttribute("aria-disabled");
    await userEvent.click(command);
    expect(screen.getByRole("dialog", { name: "Modifier la planification" })).toBeVisible();
  });

  it("keeps the answer through a reading anew of the version it answered, and gives way to a reading as recent (défaut n° 22)", async () => {
    serve();
    const { rerender } = render(
      inFrench(<BackupScheduleSection schedule={witness} locations={locations} />),
    );
    await userEvent.click(screen.getByRole("button", { name: "Modifier la planification" }));
    await retype(screen.getByRole("dialog"), "Sauvegardes conservées", "14");
    await save(screen.getByRole("dialog"));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // The page read anew serves the version 2 again — the fake back keeps nothing: the answer stays.
    rerender(inFrench(<BackupScheduleSection schedule={witness} locations={locations} />));
    const facts = screen.getByLabelText("Planification");
    expect(facts).toHaveTextContent("Rétention14 sauvegardes conservées");
    // A reading of the version 3 the answer is — suspended by another meanwhile — prevails.
    rerender(inFrench(<BackupScheduleSection schedule={disabled} locations={locations} />));
    expect(facts).toHaveTextContent("ÉtatSuspendue");
    expect(facts).toHaveTextContent("Rétention7 sauvegardes conservées");
  });

  it("offers no copy where the installation declares no location and the schedule sets none", async () => {
    const client = serve();
    const form = await openForm(weekly, []);
    expect(within(form).queryByLabelText("Copie externe vers")).toBeNull();
    expect(within(form).queryByRole("button", { name: "Tester l’emplacement" })).toBeNull();
    await save(form);
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toEqual(weekly);
  });
});

describe("the test of an external location", () => {
  beforeEach(() => {
    process.env.TZ = "UTC";
  });

  it("tests the location chosen in the folder typed, and says the witness file written then erased", async () => {
    const client = serve();
    const form = await openForm();
    await userEvent.click(within(form).getByRole("button", { name: "Tester l’emplacement" }));
    await vi.waitFor(() => {
      expect(within(form).getByRole("status")).toHaveTextContent(
        "« secours-lyon » éprouvé le 3 juin 2026, 14:05, dossier waterfall/sauvegardes : le fichier témoin a été écrit puis effacé.",
      );
    });
    expect(client.calls.map(({ path, body }) => ({ path, body }))).toEqual([
      {
        path: "/external-backup-locations/secours-lyon/test",
        body: { path: "waterfall/sauvegardes" },
      },
    ]);
  });

  it("tests a location at its root when no folder is typed, and says the motive of its failure", async () => {
    const client = serve({ [TEST]: "external_backup_location_test_failed" });
    const form = await openForm();
    await userEvent.selectOptions(within(form).getByLabelText("Copie externe vers"), "nas-siege");
    await userEvent.clear(
      within(form).getByRole("textbox", { name: "Dossier dans l’emplacement" }),
    );
    await userEvent.click(within(form).getByRole("button", { name: "Tester l’emplacement" }));
    await vi.waitFor(() => {
      expect(within(form).getByRole("status")).toHaveTextContent(
        "« nas-siege » éprouvé le 3 juin 2026, 14:05, à sa racine : échec — Accès refusé.",
      );
    });
    expect(client.calls.map(({ path, body }) => ({ path, body }))).toEqual([
      { path: "/external-backup-locations/nas-siege/test", body: {} },
    ]);
  });

  it("says a folder the server refuses under the test, nothing being tested", async () => {
    serve({
      [TEST]: {
        problem: example("external_backup_location_test_path_invalid") as Problem & {
          status: 422;
        },
      },
    });
    const form = await openForm();
    await userEvent.click(within(form).getByRole("button", { name: "Tester l’emplacement" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "Chemin invalide : il doit être relatif, sans « .. ».",
    );
    expect(within(form).getByRole("status")).toHaveTextContent("");
    // Once the folder is corrected, the refusal of the one tested is no longer said.
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Dossier dans l’emplacement" }),
      "s",
    );
    expect(within(form).queryByRole("alert")).toBeNull();
  });

  it("says nothing of a test of another location: an answer arrives once another is chosen, and falls", async () => {
    const { timing, release } = held();
    const client = serve(
      {
        [TEST]: {
          problem: example("external_backup_location_test_path_invalid") as Problem & {
            status: 422;
          },
        },
      },
      timing,
    );
    const form = await openForm();
    await userEvent.click(within(form).getByRole("button", { name: "Tester l’emplacement" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    await userEvent.selectOptions(within(form).getByLabelText("Copie externe vers"), "nas-siege");
    release();
    await vi.waitFor(() => {
      expect(settled.tests).toBe(1);
    });
    // Whatever the answer would have rendered is rendered by now.
    await act(async () => {
      await Promise.resolve();
    });
    expect(within(form).getByRole("status")).toHaveTextContent("");
    expect(within(form).queryByRole("alert")).toBeNull();
  });

  it("says the answer of the last test asked alone: one answered after it is left to fall (défaut n° 1)", async () => {
    const releases: (() => void)[] = [];
    const client = serve(
      {
        [TEST]: [
          {
            problem: example("external_backup_location_test_path_invalid") as Problem & {
              status: 422;
            },
          },
          "external_backup_location_tested",
        ],
      },
      {
        hold: (_route, index) =>
          index === 0
            ? new Promise((release) => {
                releases.push(() => {
                  release(undefined);
                });
              })
            : undefined,
      },
    );
    const form = await openForm();
    const test = within(form).getByRole("button", { name: "Tester l’emplacement" });
    await userEvent.click(test);
    await userEvent.click(test);
    // The second test, answered first.
    await vi.waitFor(() => {
      expect(within(form).getByRole("status")).toHaveTextContent(/^« secours-lyon » éprouvé/);
    });
    for (const release of releases) {
      release();
    }
    // Both answered, the test is no longer under way: the first answer, a refusal, fell.
    await vi.waitFor(() => {
      expect(test).toHaveTextContent("Tester l’emplacement");
    });
    expect(within(form).queryByRole("alert")).toBeNull();
    expect(within(form).getByRole("status")).toHaveTextContent(/^« secours-lyon » éprouvé/);
    // Both asked of the location chosen, in the folder typed.
    expect(client.calls.map(({ path, body }) => ({ path, body }))).toEqual(
      Array.from({ length: 2 }, () => ({
        path: "/external-backup-locations/secours-lyon/test",
        body: { path: "waterfall/sauvegardes" },
      })),
    );
  });
});
