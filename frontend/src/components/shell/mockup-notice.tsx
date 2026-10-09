// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The notice of a screen of the mock-up whose commands write (EP-02/L43): the fake back answers each
 * write by an example of the contract and keeps nothing, so that a reading anew shows what it served
 * before, save the rows the screen shows as the server answered their writes while it stays open
 * (`useAnswered`) — the screen says it once, discreetly, under its header, rather than simulating a
 * list that keeps what was written. It goes with the fake back: a screen wired to the service of its epic no
 * longer shows it (EP-05 for the reference data).
 *
 * Neither server nor client: it takes nothing, and renders on either side.
 */
import { FlaskConical } from "lucide-react";
import { useTranslations } from "next-intl";

/** Say that what the commands of the screen write is not kept. */
export function MockupNotice() {
  const t = useTranslations("mockup");
  return (
    <p role="note" className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <FlaskConical aria-hidden="true" className="size-3.5 shrink-0" />
      {t("notKept")}
    </p>
  );
}
