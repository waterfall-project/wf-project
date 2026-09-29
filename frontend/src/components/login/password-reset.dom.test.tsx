// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { AskResetLink, ChoosePassword } from "./password-reset";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const TOKEN = "a-token-of-twenty-characters";
const CONFIRM = "POST /session/password-reset/confirm";

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

/** Type a new password, and save it. */
async function choose(password: string) {
  await userEvent.type(screen.getByLabelText("Nouveau mot de passe"), password);
  await userEvent.click(screen.getByRole("button", { name: "Enregistrer le mot de passe" }));
}

describe("the password forgotten", () => {
  it("sends the address to the API, and says a link is sent without saying whether an account has it", async () => {
    const client = serve({ "POST /session/password-reset": { status: 202 } });
    const { container } = render(inFrench(<AskResetLink />));
    const status = screen.getByRole("status");
    expect(status).toBeEmptyDOMElement();

    await userEvent.type(
      screen.getByLabelText("Adresse électronique"),
      "camille.martin@example.com",
    );
    await userEvent.click(screen.getByRole("button", { name: "Envoyer le lien" }));

    expect(status).toHaveTextContent(
      "Si un compte correspond à cette adresse, un lien vient de lui être envoyé.",
    );
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      ["POST /session/password-reset", { email: "camille.martin@example.com" }],
    ]);
    await expectAccessible(container);
  });

  it("sets the new password with the token of the link, and leads to the sign-in page", async () => {
    const client = serve({ [CONFIRM]: { status: 204 } });
    render(inFrench(<ChoosePassword token={TOKEN} />));

    // No rule of the password in the front: a short one goes to the API, which judges it.
    await choose("court");

    expect(client.calls.map(({ body }) => body)).toEqual([{ token: TOKEN, password: "court" }]);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(
      "Votre mot de passe est enregistré : vous pouvez vous connecter.",
    );
    expect(within(status).getByRole("link", { name: "Se connecter" })).toHaveAttribute(
      "href",
      "/login",
    );
    expect(screen.queryByRole("button", { name: "Enregistrer le mot de passe" })).toBeNull();
  });

  it("tells a password the API refuses by the code of the catalogue", async () => {
    serve({ [CONFIRM]: { problem: { code: "VALIDATION_FAILED", status: 422 } } });
    render(inFrench(<ChoosePassword token={TOKEN} />));
    await choose("court");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Les données saisies ne sont pas valides.",
    );
    expect(screen.getByRole("button", { name: "Enregistrer le mot de passe" })).toBeEnabled();
  });

  it("offers to ask for a new link when the one followed has expired or served already", async () => {
    serve({ [CONFIRM]: { problem: { code: "PASSWORD_RESET_TOKEN_INVALID", status: 409 } } });
    render(inFrench(<ChoosePassword token={TOKEN} />));
    await choose("un mot de passe assez long");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ce lien de réinitialisation n’est plus valable.",
    );
    expect(screen.getByRole("link", { name: "Demander un nouveau lien" })).toHaveAttribute(
      "href",
      "/login/reset",
    );
  });
});
