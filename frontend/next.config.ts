// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Configuration of the Next.js application.
 */
import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // The front calls nothing but the API, through the generated client (WF-ARC-0020).
  poweredByHeader: false,
};

export default config;
