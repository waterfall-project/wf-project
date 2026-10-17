-- SPDX-FileCopyrightText: 2026 waterfall-project
-- SPDX-License-Identifier: AGPL-3.0-only

-- The database of Keycloak on the server of Waterfall: a database and a role of its own (#215,
-- PBS-3.1), created when missing, at each start of the platform; the password of the role follows
-- the environment, read by psql from KEYCLOAK_DATABASE_PASSWORD, never from a command line.
\getenv keycloak_password KEYCLOAK_DATABASE_PASSWORD
SELECT 'CREATE ROLE keycloak LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'keycloak') \gexec
ALTER ROLE keycloak PASSWORD :'keycloak_password';
SELECT 'CREATE DATABASE keycloak OWNER keycloak'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak') \gexec
