// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import type { components } from "@/api/generated/schema";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { AvatarForm } from "./avatar-form";
import { AvatarPicture } from "./avatar-picture";
import { PreferencesForm } from "./preferences-form";

// The server of Next, as far as the forms need it: the fake back behind serverClient, and the
// refresh a server action asks for, which renders the page again.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ refresh: () => undefined }),
  usePathname: () => "/account",
  useSearchParams: () => new URLSearchParams(),
}));

const PREFERENCES = "PATCH /me/preferences";
// The eight bytes that open every PNG file, standing for an image.
const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
// The largest avatar the installation admits: two megabytes.
const { avatar_max_bytes: MAX_BYTES } = example(
  "installation",
) as components["schemas"]["Installation"];

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** A page in French, as the shell hands it its texts. */
function inFrench(page: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {page}
    </NextIntlClientProvider>
  );
}

/**
 * Serve the fake back, its answers held until the test lets them go: what the screen shows while
 * a request is under way.
 */
function holding(answers: FakeAnswers): () => void {
  let give: () => void = () => undefined;
  const released = new Promise<void>((resolve) => {
    give = resolve;
  });
  server.client = fakeClient(answers, { hold: () => released });
  return () => {
    give();
  };
}

/** The bodies sent to an operation. */
function sent(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

beforeEach(() => {
  refresh.mockReset();
});

describe("the preferences on the screen of the account", () => {
  it("records the language and the mode chosen, the same fields the menu of the account writes", async () => {
    const client = serve({ [PREFERENCES]: "preferences_dark" });
    const { container } = render(inFrench(<PreferencesForm language="default" theme="default" />));
    await expectAccessible(container);
    const language = screen.getByRole("radiogroup", { name: "Langue" });
    const mode = screen.getByRole("radiogroup", { name: "Mode d’affichage" });
    expect(within(language).getByRole("radio", { name: "Langue du navigateur" })).toBeChecked();

    await userEvent.click(within(language).getByRole("radio", { name: "English" }));
    await userEvent.click(within(mode).getByRole("radio", { name: "Sombre" }));
    // Choosing sends nothing: the preferences go when the user saves them.
    expect(sent(client, PREFERENCES)).toEqual([]);
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(sent(client, PREFERENCES)).toEqual([{ language: "en", theme: "dark" }]);
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.getByRole("status")).toHaveTextContent("Vos préférences sont enregistrées.");
  });

  it("sends nothing while the keyboard moves through the values", async () => {
    const client = serve({ [PREFERENCES]: "preferences" });
    render(inFrench(<PreferencesForm language="default" theme="default" />));
    await userEvent.tab();
    expect(screen.getByRole("radio", { name: "Langue du navigateur" })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}{ArrowDown}");
    expect(screen.getByRole("radio", { name: "English" })).toHaveFocus();
    await userEvent.keyboard(" ");
    expect(screen.getByRole("radio", { name: "English" })).toBeChecked();
    expect(sent(client, PREFERENCES)).toEqual([]);
  });

  it("holds the values while the choice is recorded, so that none chosen meanwhile is lost", async () => {
    const answer = holding({ [PREFERENCES]: "preferences" });
    render(inFrench(<PreferencesForm language="default" theme="default" />));
    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    const save = screen.getByRole("button", { name: "Enregistrer" });
    await userEvent.click(save);

    expect(screen.getByRole("radio", { name: "Français" })).toBeDisabled();
    expect(screen.getByRole("radio", { name: "Sombre" })).toBeDisabled();
    // The button stays where the focus is, and does nothing more meanwhile.
    expect(save).toHaveFocus();
    expect(save).toHaveAttribute("aria-disabled", "true");

    answer();
    await waitFor(() => {
      expect(screen.getByRole("radio", { name: "Français" })).toBeEnabled();
    });
    expect(screen.getByRole("radio", { name: "English" })).toBeChecked();
  });

  it("starts again from the preferences a new render gives: those saved, or those chosen in the menu", () => {
    const view = render(inFrench(<PreferencesForm language="default" theme="default" />));
    view.rerender(inFrench(<PreferencesForm language="fr" theme="light" />));
    expect(screen.getByRole("radio", { name: "Français" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Clair" })).toBeChecked();
  });

  it("says a deactivated account instead of leading to the sign-in page, which would loop", async () => {
    serve({ [PREFERENCES]: { problem: { code: "ACCOUNT_DEACTIVATED", status: 401 } } });
    render(inFrench(<PreferencesForm language="default" theme="default" />));
    await userEvent.click(screen.getByRole("radio", { name: "Français" }));
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Ce compte est désactivé ; contactez un administrateur.");
    expect(within(alert).queryByRole("link", { name: "Se connecter" })).toBeNull();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("leads to the sign-in page when the session is gone, and keeps the choice", async () => {
    serve({ [PREFERENCES]: { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    render(inFrench(<PreferencesForm language="default" theme="default" />));
    await userEvent.click(screen.getByRole("radio", { name: "Français" }));
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByRole("link", { name: "Se connecter" })).toHaveAttribute(
      "href",
      "/login?next=%2Faccount",
    );
    expect(screen.getByRole("radio", { name: "Français" })).toBeChecked();
    expect(refresh).not.toHaveBeenCalled();
  });
});

describe("the avatar of the account", () => {
  it("puts the PNG or JPEG image chosen, and says it is saved", async () => {
    const client = serve({ "PUT /me/avatar": { status: 204 } });
    const { container } = render(inFrench(<AvatarForm hasAvatar={false} maxBytes={MAX_BYTES} />));
    await expectAccessible(container);
    const upload = screen.getByRole("button", { name: "Déposer l’image" });
    expect(upload).toHaveAttribute("aria-disabled", "true");
    expect(screen.queryByRole("button", { name: "Retirer l’avatar" })).toBeNull();

    await userEvent.upload(
      screen.getByLabelText("Image PNG ou JPEG"),
      new File([PNG], "camille.png", { type: "image/png" }),
    );
    await userEvent.click(upload);

    const [body] = sent(client, "PUT /me/avatar");
    expect(body).toBeInstanceOf(Blob);
    expect((body as Blob).type).toBe("image/png");
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.getByRole("status")).toHaveTextContent("Votre avatar est enregistré.");
    await waitFor(() => {
      expect(upload).toHaveAttribute("aria-disabled", "true");
    });
  });

  it("says a file of another kind is no avatar, rather than send what the API would refuse", async () => {
    const client = serve({ "PUT /me/avatar": { status: 204 } });
    render(inFrench(<AvatarForm hasAvatar={false} maxBytes={MAX_BYTES} />));
    const field = screen.getByLabelText("Image PNG ou JPEG");
    await userEvent.upload(field, new File([PNG], "camille.gif", { type: "image/gif" }), {
      applyAccept: false,
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Choisissez une image PNG ou JPEG.");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription(
      "Une image de 2\u00A0mégaoctets au plus. Choisissez une image PNG ou JPEG.",
    );
    const upload = screen.getByRole("button", { name: "Déposer l’image" });
    expect(upload).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(upload);
    expect(client.calls).toEqual([]);
  });

  it("holds the choice of an image while one is sent", async () => {
    const answer = holding({ "PUT /me/avatar": { status: 204 } });
    render(inFrench(<AvatarForm hasAvatar={false} maxBytes={MAX_BYTES} />));
    const field = screen.getByLabelText("Image PNG ou JPEG");
    await userEvent.upload(field, new File([PNG], "camille.png", { type: "image/png" }));
    await userEvent.click(screen.getByRole("button", { name: "Déposer l’image" }));
    expect(field).toBeDisabled();

    answer();
    await waitFor(() => {
      expect(field).toBeEnabled();
    });
    expect(screen.getByRole("status")).toHaveTextContent("Votre avatar est enregistré.");
  });

  it("says the largest image the installation admits before one is chosen", () => {
    render(inFrench(<AvatarForm hasAvatar={false} maxBytes={MAX_BYTES} />));
    expect(screen.getByLabelText("Image PNG ou JPEG")).toHaveAccessibleDescription(
      "Une image de 2\u00A0mégaoctets au plus.",
    );
  });

  it("refuses an image larger than the installation admits, says so, and sends nothing", async () => {
    const client = serve({ "PUT /me/avatar": { status: 204 } });
    render(inFrench(<AvatarForm hasAvatar={false} maxBytes={MAX_BYTES} />));
    const field = screen.getByLabelText("Image PNG ou JPEG");
    const heavy = new Uint8Array(MAX_BYTES + 1);
    heavy.set(PNG);
    await userEvent.upload(field, new File([heavy], "camille.png", { type: "image/png" }));
    const refusal = "Cette image dépasse 2\u00A0mégaoctets\u00A0: choisissez-en une plus légère.";
    // The text content of an element reads every space as a plain one.
    expect(screen.getByRole("alert")).toHaveTextContent(refusal.replaceAll("\u00A0", " "));
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription(`Une image de 2\u00A0mégaoctets au plus. ${refusal}`);
    const upload = screen.getByRole("button", { name: "Déposer l’image" });
    expect(upload).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(upload);
    expect(client.calls).toEqual([]);

    // An image of the bound exactly is sent.
    await userEvent.upload(
      field,
      new File([heavy.subarray(0, MAX_BYTES)], "camille.png", { type: "image/png" }),
    );
    expect(screen.queryByRole("alert")).toBeNull();
    await userEvent.click(upload);
    expect(sent(client, "PUT /me/avatar")).toHaveLength(1);
  });

  it("tells an image the API finds too large", async () => {
    serve({ "PUT /me/avatar": { problem: { code: "FILE_TOO_LARGE", status: 413 } } });
    render(inFrench(<AvatarForm hasAvatar={false} maxBytes={MAX_BYTES} />));
    await userEvent.upload(
      screen.getByLabelText("Image PNG ou JPEG"),
      new File([PNG], "camille.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Déposer l’image" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le fichier dépasse la taille admise.",
    );
    expect(refresh).not.toHaveBeenCalled();
  });

  it("withdraws the avatar the account has, and says it is withdrawn", async () => {
    const client = serve({ "DELETE /me/avatar": { status: 204 } });
    render(inFrench(<AvatarForm hasAvatar maxBytes={MAX_BYTES} />));
    await userEvent.click(screen.getByRole("button", { name: "Retirer l’avatar" }));
    expect(client.calls.map((call) => call.route)).toEqual(["DELETE /me/avatar"]);
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.getByRole("status")).toHaveTextContent("Votre avatar est retiré.");
    // Its button goes with the avatar: the focus goes to the choice of an image.
    expect(screen.getByLabelText("Image PNG ou JPEG")).toHaveFocus();
  });
});

describe("the picture of the avatar", () => {
  it("shows the image the page holds, named after the account, once loaded", async () => {
    const source = `data:image/png;base64,${Buffer.from(PNG).toString("base64")}`;
    const account = { first_name: "Camille", last_name: "Martin" };
    // happy-dom loads an image without decoding it: its width, which says a browser decoded it,
    // is given here.
    const decoded = vi
      .spyOn(window.HTMLImageElement.prototype, "naturalWidth", "get")
      .mockReturnValue(96);
    render(inFrench(<AvatarPicture account={account} source={source} />));
    const image = await screen.findByRole("img", { name: "Camille Martin" });
    expect(image).toHaveAttribute("src", source);
    expect(screen.queryByText("CM")).toBeNull();
    decoded.mockRestore();
  });

  it("shows the initials of an account without an image", () => {
    render(
      inFrench(
        <AvatarPicture
          account={{ first_name: "Camille", last_name: "Martin" }}
          source={undefined}
        />,
      ),
    );
    expect(screen.getByText("CM")).toBeInTheDocument();
    expect(screen.queryByRole("img")).toBeNull();
  });
});
