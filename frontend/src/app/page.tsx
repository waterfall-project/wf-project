// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Home page. The screens arrive with EP-02; until then the page names the product, whose
 * name the catalogue gives like any other text.
 */
import { House } from "lucide-react";
import { useTranslations } from "next-intl";

import { PageHeader, Screen } from "@/components/shell/page-header";

/** Render the home page. */
export default function HomePage() {
  const t = useTranslations("app");
  return (
    <Screen>
      <PageHeader title={t("name")} icon={House} />
    </Screen>
  );
}
