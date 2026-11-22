-- SPDX-FileCopyrightText: 2026 waterfall-project
-- SPDX-License-Identifier: AGPL-3.0-only

-- The role of the backup (#895): the worker dumps the two databases of the server as it, never as
-- the owner of the tables nor as a superuser, who could give themselves back the rights or turn off
-- the trigger of the journal of audit (#701). A member of pg_read_all_data, it reads every table of
-- every database, and can neither write nor turn a trigger off; it owns nothing. Created when
-- missing, at each start of the platform; its password follows the environment, read by psql from
-- BACKUP_DATABASE_PASSWORD, never from a command line.
\getenv backup_password BACKUP_DATABASE_PASSWORD
SELECT 'CREATE ROLE waterfall_backup LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'waterfall_backup') \gexec
ALTER ROLE waterfall_backup LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS
    PASSWORD :'backup_password';
GRANT pg_read_all_data TO waterfall_backup;

-- The large objects of the database of Keycloak (#4170): pg_read_all_data reads the tables, the
-- views and the sequences, not the large objects, and a pg_dump of a database that holds one fails,
-- the whole backup with it. Keycloak keeps some in a column of its own (cluster_event.event_data).
-- The right is granted in that database, whose default privileges are its own: on the objects
-- Keycloak creates from now on, and, at each start, on those it created before. The database exists
-- by now: the platform creates it before this script (keycloak-database).
\connect keycloak
ALTER DEFAULT PRIVILEGES FOR ROLE keycloak GRANT SELECT ON LARGE OBJECTS TO waterfall_backup;
SELECT format('GRANT SELECT ON LARGE OBJECT %s TO waterfall_backup', oid)
FROM pg_largeobject_metadata \gexec
