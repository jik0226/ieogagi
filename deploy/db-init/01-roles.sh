#!/bin/sh
# Runs once when the database volume is first created.
# psql reads the role passwords from the Docker secret files itself (\set with a
# backquoted cat inside the script on stdin), so they never appear on any command
# line (ps, /proc/<pid>/cmdline). They reach SQL only as psql variables with
# :'name' quoting, never concatenated into SQL text.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<'SQL'
\set owner_pw `cat /run/secrets/owner_password`
\set app_pw `cat /run/secrets/app_password`
CREATE ROLE ieogagi_owner LOGIN PASSWORD :'owner_pw';
CREATE ROLE ieogagi_app LOGIN PASSWORD :'app_pw';
\unset owner_pw
\unset app_pw
CREATE DATABASE ieogagi OWNER ieogagi_owner;
REVOKE CONNECT ON DATABASE ieogagi FROM PUBLIC;
GRANT CONNECT ON DATABASE ieogagi TO ieogagi_owner, ieogagi_app;
SQL
