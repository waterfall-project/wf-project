// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only

// The variables of the cache that the builder of Docker reads (type=gha), those the runner sets:
// written to the environment of the steps that follow, never printed. The runner masks the token.
import { appendFileSync } from "node:fs";

const NAMES = [
  "ACTIONS_CACHE_URL",
  "ACTIONS_CACHE_SERVICE_V2",
  "ACTIONS_RESULTS_URL",
  "ACTIONS_RUNTIME_TOKEN",
];

const lines = NAMES.filter((name) => process.env[name]).map(
  (name) => `${name}=${process.env[name]}\n`,
);
appendFileSync(process.env.GITHUB_ENV, lines.join(""));
