"""Tenant isolation with row-level security (SAPS-41, ADR-0009).

Roles `saps_app` (SAPS API, worker jobs) and `saps_system` (sweeper, BYPASSRLS); RLS enabled and forced on every
tenant-owned table with the policy `tenant_isolation`; two SECURITY DEFINER lookups used before the company is known.
The role passwords come from the settings (`APP_DB_PASSWORD`, `SYSTEM_DB_PASSWORD`).

Revision ID: 0006
Revises: 0005
Create Date: 2027-03-01
"""

from collections.abc import Sequence

from alembic import op

from saps.config import get_settings

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "user_account",
    "user_session",
    "matching_settings",
    "invoice",
    "invoice_line",
    "invoice_exception",
    "approval",
    "invoice_event",
    "notification",
)
APP_ROLE = "saps_app"
# Unset → NULL; a connection that had the setting before reports '' afterwards, which must also mean "no company".
CURRENT_TENANT = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
SYSTEM_ROLE = "saps_system"


def _literal(value: str) -> str:
    """A SQL string literal; role passwords cannot be bound as parameters in ALTER ROLE."""
    if "\x00" in value:
        raise ValueError("A role password must not contain NUL characters.")
    return "'" + value.replace("'", "''") + "'"


def _create_role(name: str, options: str, password: str) -> None:
    op.execute(
        f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{name}') "
        f"THEN CREATE ROLE {name} {options}; END IF; END $$"
    )
    op.execute(f"ALTER ROLE {name} {options} PASSWORD {_literal(password)}")


def upgrade() -> None:
    settings = get_settings()
    _create_role(APP_ROLE, "LOGIN NOBYPASSRLS", settings.app_db_password.get_secret_value())
    _create_role(SYSTEM_ROLE, "LOGIN BYPASSRLS", settings.system_db_password.get_secret_value())

    for role in (APP_ROLE, SYSTEM_ROLE):
        op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"
        )
    op.execute(f"REVOKE ALL ON alembic_version FROM {APP_ROLE}, {SYSTEM_ROLE}")

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = {CURRENT_TENANT}) WITH CHECK (tenant_id = {CURRENT_TENANT})"
        )

    # Lookups before the company is known (SAPS-41 BR-05). Owned by saps_system, so they read past RLS even where the
    # migration user is not a superuser (Amazon RDS); they return only identifiers of the one matching row.
    op.execute(
        """
        CREATE FUNCTION saps_find_session(p_token_hash text)
        RETURNS TABLE (session_id uuid, tenant_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT s.id, s.tenant_id FROM user_session s WHERE s.token_hash = p_token_hash LIMIT 1 $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION saps_find_user_for_sign_in(p_username text)
        RETURNS TABLE (user_id uuid, tenant_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT u.id, u.tenant_id FROM user_account u WHERE u.username = p_username LIMIT 1 $$
        """
    )
    for function in ("saps_find_session(text)", "saps_find_user_for_sign_in(text)"):
        op.execute(f"ALTER FUNCTION {function} OWNER TO {SYSTEM_ROLE}")
        op.execute(f"REVOKE ALL ON FUNCTION {function} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {function} TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS saps_find_session(text)")
    op.execute("DROP FUNCTION IF EXISTS saps_find_user_for_sign_in(text)")
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for role in (APP_ROLE, SYSTEM_ROLE):
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') THEN "
            f"EXECUTE 'DROP OWNED BY {role}'; EXECUTE 'DROP ROLE {role}'; END IF; END $$"
        )
