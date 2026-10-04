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
  experimental: {
    serverActions: {
      // An avatar goes from the browser to the server of Next by a server action, whose body Next
      // bounds to 1 MB by default: past it, the action fails before the API is asked, and the
      // screen of failure shows instead of the refusal of the API (#221). The bound is a setting
      // of the installation (`Installation.avatar_max_bytes`, §4.4.1), which the contract does
      // not bound yet (#233): ten megabytes, the form around the image included, hold only as
      // long as it does not, and follow the maximum the contract will declare.
      bodySizeLimit: "10mb",
    },
  },
};

// next-intl, without the language in the address: the plugin finds the configuration of a
// request at its default path, src/i18n/request.ts.
export default createNextIntlPlugin()(config);
