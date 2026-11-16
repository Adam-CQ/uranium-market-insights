#!/bin/bash
# Sourced by the official PostgreSQL entrypoint on a NEW production volume only.
# psql reads the password from its environment, without echoing it or using argv.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 <<'SQL'
\getenv reader_password API_DB_PASSWORD
CREATE ROLE uranium_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'reader_password';
GRANT CONNECT ON DATABASE uranium TO uranium_reader;
GRANT USAGE ON SCHEMA public TO uranium_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE dashboard IN SCHEMA public GRANT SELECT ON TABLES TO uranium_reader;
SQL
