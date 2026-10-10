-- SPDX-FileCopyrightText: 2026 waterfall-project
-- SPDX-License-Identifier: AGPL-3.0-only

-- The role of the service, which the migrations create without the right to sign in (0002): it
-- may now, with the password of the environment, read by psql from SERVICE_DATABASE_PASSWORD,
-- never from a command line. It owns nothing, and holds only what the tables grant it.
\getenv service_password SERVICE_DATABASE_PASSWORD
ALTER ROLE waterfall_service LOGIN PASSWORD :'service_password';
