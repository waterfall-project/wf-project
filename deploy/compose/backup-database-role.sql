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
