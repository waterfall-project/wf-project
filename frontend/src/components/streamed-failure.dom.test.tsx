// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The failure of what a screen reads apart from its grid — its indicators — surfaces once the shell
 * is sent, under a boundary of suspense (US-2290, #3630). The screen of failure shows it all the
 * same, in place of the page, by the digest the error carries: the session required, the
 * correlation identifier, the service out of reach. Next forwards the error of a server component
 * to the client with that digest, as a generic error does here.
 */
import { act, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { Component, type ReactNode, Suspense } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import PageError from "@/app/error";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  type BoundaryError,
  correlationDigest,
  SESSION_REQUIRED_DIGEST,
  UNREACHABLE_DIGEST,
} from "@/components/system/failure";
import { takeStderr } from "@/test/stderr";

import { Streamed } from "./streamed";

// The address the browser shows, as the router of Next gives it to a client component.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/projects/p/revisions/r/remaining",
  useSearchParams: () => new URLSearchParams("work_package_id=lot"),
}));

// A whole document loaded: the sign-in page, which the test only records.
vi.mock("@/navigation/document", () => ({ loadDocument: vi.fn() }));

// The probe that says the maintenance of a restoration: the platform serves.
vi.mock("@/api/actions/backups", () => ({ readLiveness: () => Promise.resolve("ok") }));

/** An error as Next forwards it from the server in production: a generic message, a digest. */
function forwarded(digest: string): BoundaryError {
  return Object.assign(new Error("An error occurred in the Server Components render."), {
    digest,
  });
}

/** The boundary of the pages of Next: it hands the error it caught to `app/error.tsx`. */
class PageBoundary extends Component<{ children: ReactNode }, { error: BoundaryError | null }> {
  override state: { error: BoundaryError | null } = { error: null };
  static getDerivedStateFromError(error: BoundaryError) {
    return { error };
  }
  override render() {
    return this.state.error === null ? (
      this.props.children
    ) : (
      <PageError error={this.state.error} retry={() => undefined} />
    );
  }
}

/** Run what changes the screen inside `act`, awaited: a render may suspend in it. */
async function inAct(work: () => void) {
  await act(async () => {
    work();
    await Promise.resolve();
  });
}

/** The screen as the page makes it, its indicators read by the server apart from the rest. */
async function failing(error: BoundaryError) {
  // The read fails once the shell is sent, as the stream of the server says it to the client.
  const content = Promise.reject<ReactNode>(error);
  content.catch(() => undefined);
  await inAct(() => {
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <PageBoundary>
          <p>grille</p>
          <Suspense fallback={<p>chargement</p>}>
            <Streamed content={content} />
          </Suspense>
        </PageBoundary>
      </NextIntlClientProvider>,
    );
  });
}

afterEach(() => {
  // React logs the error it handed to the boundary: that is what the test expects of it.
  expect(takeStderr().join("\n")).toContain("An error occurred in the Server Components render.");
});

describe("the failure of the indicators read apart from the grid", () => {
  it("shows the screen of failure of the session required, with the way to sign in [WF-SEC-0020-A]", async () => {
    await failing(forwarded(SESSION_REQUIRED_DIGEST));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Session requise");
    expect(screen.getByRole("link", { name: "Se connecter" })).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent("/projects/p/revisions/r/remaining?work_package_id=lot")}`,
    );
    expect(screen.queryByText("grille")).toBeNull();
  });

  it("shows the screen of failure with the correlation identifier of the error", async () => {
    await failing(forwarded(correlationDigest("req-9b1c")));
    expect(screen.getByRole("alert")).toHaveTextContent("Référence : req-9b1c");
  });

  it("shows the screen of failure of the service out of reach, with the command to try again", async () => {
    await failing(forwarded(UNREACHABLE_DIGEST));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Service injoignable");
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeVisible();
  });
});
