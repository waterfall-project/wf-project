-- SPDX-FileCopyrightText: 2026 waterfall-project
-- SPDX-License-Identifier: AGPL-3.0-only

-- The database of Waterfall and its owner, waterfall, created when missing, at each start of the
-- production platform, by the administrator of the server (US-0430). The owner of the tables
-- migrates and bootstraps (#701); it is no superuser, and can create neither a role nor a database:
-- whoever holds its password holds the tables of Waterfall, not the server nor Keycloak's database.
-- The role of the service, which migration 0002 would create, is created here first, without the
-- right to sign in: creating a role is the administrator's (service-database-role.sql lets it sign
-- in). The password of the owner follows the environment, read by psql from
-- OWNER_DATABASE_PASSWORD, never from a command line.
\getenv owner_password OWNER_DATABASE_PASSWORD
SELECT 'CREATE ROLE waterfall LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'waterfall') \gexec
ALTER ROLE waterfall LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
    PASSWORD :'owner_password';
SELECT 'CREATE ROLE waterfall_service NOLOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'waterfall_service') \gexec
SELECT 'CREATE DATABASE waterfall OWNER waterfall'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'waterfall') \gexec
