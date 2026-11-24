#!/bin/sh
# Creates the database and the role of Keycloak in the SAPS Database container (SAPS-43). Safe to run again:
# an existing role gets the current password, an existing database is kept. Run by the `db-init` service.
set -eu
export PGPASSWORD="$POSTGRES_PASSWORD"
psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -v kcpw="$KEYCLOAK_DB_PASSWORD" <<'SQL'
SELECT 'CREATE ROLE keycloak LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'keycloak') \gexec
SELECT format('ALTER ROLE keycloak PASSWORD %L', :'kcpw') \gexec
SELECT 'CREATE DATABASE keycloak OWNER keycloak' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak') \gexec
SQL
