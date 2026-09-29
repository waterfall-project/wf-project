// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The skeleton a screen shows while the server reads the API for it: the outline of a title
 * and of rows, in place of the page to come, so that a loading shows. The page region is
 * busy, and named so; `aria-busy` alone says nothing, so a status, hidden from the eye, tells
 * a screen reader that the screen loads — not the shapes, which are hidden from it. The pulse
 * stops when the workstation asks for less motion.
 */
import { useTranslations } from "next-intl";

const ROWS = ["w-full", "w-11/12", "w-5/6", "w-2/3"] as const;
const BLOCK = "rounded-md bg-muted motion-safe:animate-pulse";

/** Render the skeleton of a screen that loads. */
export function ScreenSkeleton() {
  const t = useTranslations("loading");
  return (
    <main aria-busy="true" aria-label={t("label")} className="space-y-4 p-6">
      <p role="status" aria-label={t("label")} className="sr-only">
        {t("label")}
      </p>
      <div aria-hidden="true" className="space-y-4">
        <div className={`h-8 w-1/3 ${BLOCK}`} />
        {ROWS.map((width) => (
          <div key={width} className={`h-5 ${width} ${BLOCK}`} />
        ))}
      </div>
    </main>
  );
}
