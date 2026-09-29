// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The skeleton a screen shows while the server reads the API for it: the outline of a title
 * and of rows, in place of the page to come, so that a loading shows. The page region is
 * named for the loading; the shapes are hidden from a screen reader, and they alone are
 * marked busy. A status, hidden from the eye and outside the busy block — a busy region may
 * hold back what it contains —, says that the screen loads: a reader finds it by its role and
 * its name. Whether it is spoken as it appears depends on the reader: a live region inserted
 * with its text already in it is not announced by every one. The pulse stops when the
 * workstation asks for less motion.
 */
import { useTranslations } from "next-intl";

const ROWS = ["w-full", "w-11/12", "w-5/6", "w-2/3"] as const;
const BLOCK = "rounded-md bg-muted motion-safe:animate-pulse";

/** Render the skeleton of a screen that loads. */
export function ScreenSkeleton() {
  const t = useTranslations("loading");
  return (
    <main aria-label={t("label")} className="space-y-4 p-6">
      <p role="status" aria-label={t("label")} className="sr-only">
        {t("label")}
      </p>
      <div aria-hidden="true" aria-busy="true" className="space-y-4">
        <div className={`h-8 w-1/3 ${BLOCK}`} />
        {ROWS.map((width) => (
          <div key={width} className={`h-5 ${width} ${BLOCK}`} />
        ))}
      </div>
    </main>
  );
}
