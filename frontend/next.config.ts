// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Configuration of the Next.js application.
 */
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// The hosts besides localhost that the browser may open the development server at: `next dev`
// refuses its resources (`/_next/*`, the hot reload) to any other origin, and the page then shows
// without the JavaScript that hydrates it (#481). The addresses of a local network are each
// workstation's own, so they come from the environment: hosts separated by commas.
const DEV_ORIGINS = (process.env.WATERFALL_DEV_ORIGINS ?? "127.0.0.1")
  .split(",")
  .map((host) => host.trim())
  .filter((host) => host !== "");

const config: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: DEV_ORIGINS,
  // The front calls nothing but the API, through the generated client (WF-ARC-0020).
  poweredByHeader: false,
  experimental: {
    serverActions: {
      // An avatar and the file of an import go from the browser to the server of Next by a server
      // action, whose body Next bounds to 1 MB by default: past it, the action fails before the
      // API is asked, and the screen of failure shows instead of the refusal of the API (#221).
      // The contract bounds the deposit of an import at 10 MiB (`uploadFile`, `purpose: import`,
      // an MS Project file of §4.6.2), which the screen of the imports refuses beyond in the page
      // (`IMPORT_MAX_BYTES`), and the avatar at 8 MiB at most (`Installation.avatar_max_bytes`):
      // twelve megabytes hold the larger, and the multipart form around it.
      bodySizeLimit: "12mb",
    },
  },
};

// next-intl, without the language in the address: the plugin finds the configuration of a
// request at its default path, src/i18n/request.ts.
export default createNextIntlPlugin()(config);
