-- SPDX-FileCopyrightText: 2026 waterfall-project
-- SPDX-License-Identifier: AGPL-3.0-only

-- The role of the service, which the migrations create without the right to sign in (0002), named
-- after the database — waterfall_service here: it may now, with the password of the environment,
-- read by psql from SERVICE_DATABASE_PASSWORD, never from a command line. It owns nothing, and
-- holds only what the tables of this database grant it.
\getenv service_password SERVICE_DATABASE_PASSWORD
SELECT current_database() || '_service' AS service_role \gset
ALTER ROLE :"service_role" LOGIN PASSWORD :'service_password';
