-- SPDX-FileCopyrightText: 2026 waterfall-project
-- SPDX-License-Identifier: AGPL-3.0-only

-- The databases of the ephemeral platform of the test of a restoration (US-2930,
-- compose.restore-test.yaml), made at the initialisation of its PostgreSQL, empty: the owner of
-- Waterfall's, who restores it and migrates it, and the role of the service, without the right to
-- sign in, which the migrations grant to (waterfall-database.sql); the owner of Keycloak's
-- (keycloak-database.sql). Their password is the one of the test, which restore-test.sh draws, read
-- by psql from RESTORE_TEST_PASSWORD, never from a command line.
\getenv password RESTORE_TEST_PASSWORD
CREATE ROLE waterfall LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
    PASSWORD :'password';
CREATE ROLE waterfall_service NOLOGIN;
CREATE DATABASE waterfall OWNER waterfall;
CREATE ROLE keycloak LOGIN PASSWORD :'password';
CREATE DATABASE keycloak OWNER keycloak;
