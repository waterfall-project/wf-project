// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the card of the installation shows (FBS-1.6, EP-25 US-2120): the name of the company, which
 * the exported files bear (WF-EXP-0020) and which `installation.write` modifies, and, read only,
 * what the bootstrap fixed — the currency, the default language and the time zone, none of which
 * any screen modifies (WF-REF-0140, WF-EXP-0020). Every value as the API gives it.
 */
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";

type Installation = components["schemas"]["Installation"];

/** The facts of the installation, in a list the card names. */
export function InstallationFacts({
  name,
  currency,
  installation,
}: {
  readonly name: string;
  readonly currency: string;
  readonly installation: Installation;
}) {
  const t = useTranslations("installation");
  const language = useTranslations("enums.Language");
  const facts = [
    [t("name"), name, true],
    [t("currency"), currency, false],
    [t("defaultLanguage"), language(installation.default_language), false],
    [t("timeZone"), installation.time_zone, false],
  ] as const;
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
        {facts.map(([term, value, strong]) => (
          <div key={term} className="contents">
            <dt className="text-muted-foreground">{term}</dt>
            <dd className={strong ? "font-semibold" : undefined}>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="text-sm text-muted-foreground">{t("fixed")}</p>
    </div>
  );
}
