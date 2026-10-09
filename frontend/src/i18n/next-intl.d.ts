// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The types next-intl checks the texts against: the offered languages, and the keys of the
 * reference catalogue, French. `t("a.key")` on a key it lacks fails `make typecheck-front`.
 */
import type { Catalogue } from "./catalogues";
import type { Locale } from "./locale";

declare module "next-intl" {
  interface AppConfig {
    Locale: Locale;
    Messages: Catalogue;
  }
}
