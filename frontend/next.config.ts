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
      // An avatar and the file of an import go from the browser to the server of Next by a server
      // action, whose body Next bounds to 1 MB by default: past it, the action fails before the
      // API is asked, and the screen of failure shows instead of the refusal of the API (#221).
      // The contract bounds the avatar at 8 MiB at most (`Installation.avatar_max_bytes`), not
      // yet a file deposited (#324). The largest import of the volumes of §4.6.2 is an MS
      // Project file of ten megabytes, which the screen of the imports refuses past 10 MiB
      // (`IMPORT_MAX_BYTES`): twelve megabytes hold such a file, or the largest avatar, and the
      // multipart form around it.
      bodySizeLimit: "12mb",
    },
  },
};

// next-intl, without the language in the address: the plugin finds the configuration of a
// request at its default path, src/i18n/request.ts.
export default createNextIntlPlugin()(config);
