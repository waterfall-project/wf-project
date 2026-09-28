// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Configuration of the Next.js application.
 */
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const config: NextConfig = {
  reactStrictMode: true,
  // The front calls nothing but the API, through the generated client (WF-ARC-0020).
  poweredByHeader: false,
};

// next-intl, without the language in the address: the plugin finds the configuration of a
// request at its default path, src/i18n/request.ts.
export default createNextIntlPlugin()(config);
