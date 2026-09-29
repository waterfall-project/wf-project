// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The one screen "not found", inside the shell: an address that leads to no screen, and one
 * whose object the API does not find or does not let the user read — which it answers alike
 * — show the same body, word for word; the tab keeps the title of the function the address
 * names, which says nothing of the object. Telling them apart would reveal that the object
 * exists (WF-ADM-0110). A link leads back home.
 *
 * It answers with the status 200, not 404: every segment that reads the API has its
 * `loading.tsx`, so the response streams, its status is sent with the skeleton before the
 * page knows the object is not found, and Next marks the page `noindex` instead — a soft 404.
 * The status is the same for every address not found, which is what matters here; a loading
 * seen at once is worth more to an application behind a session than a status no crawler
 * reads.
 */
import Link from "next/link";
import { useTranslations } from "next-intl";

/** Render the screen "not found". */
export default function NotFound() {
  const t = useTranslations("notFound");
  return (
    <main className="space-y-2 p-6">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="text-muted-foreground">{t("explanation")}</p>
      <Link href="/" className="font-medium underline">
        {t("home")}
      </Link>
    </main>
  );
}
