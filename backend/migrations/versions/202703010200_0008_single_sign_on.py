"""Single Sign-On (SAPS-44): users get their Identity Provider identity, sessions keep the encrypted tokens.

Passwords are dropped (NFR-SEC-001). Open sessions of the password sign-in are revoked (EC-13): users sign in again
through Keycloak and are linked to their account by e-mail (BR-03).

Revision ID: 0008
Revises: 0007
Create Date: 2027-03-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "saps_app"
SYSTEM_ROLE = "saps_system"
OLD_USER_LOOKUP = "saps_find_user_for_sign_in(text)"
NEW_FUNCTIONS = ("saps_find_user_for_sign_in(text, text, text)", "saps_find_idp_sessions(text)")


def _own(function: str) -> None:
    """Owned by saps_system, so it reads past row-level security; only the SAPS API may call it (SAPS-41)."""
    op.execute(f"ALTER FUNCTION {function} OWNER TO {SYSTEM_ROLE}")
    op.execute(f"REVOKE ALL ON FUNCTION {function} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {function} TO {APP_ROLE}")


def upgrade() -> None:
    op.add_column("user_account", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("user_account", sa.Column("idp_issuer", sa.String(255), nullable=True))
    op.add_column("user_account", sa.Column("idp_subject", sa.String(255), nullable=True))
    op.create_unique_constraint(
        "uq_user_account_idp_issuer_idp_subject", "user_account", ["idp_issuer", "idp_subject"]
    )
    # The table owner is subject to FORCE ROW LEVEL SECURITY: update every company's rows under its own setting.
    op.execute(
        """
        DO $$
        DECLARE t uuid;
        BEGIN
            FOR t IN SELECT id FROM tenant LOOP
                PERFORM set_config('app.tenant_id', t::text, true);
                UPDATE user_account SET email = lower(username) WHERE username LIKE '%@%' AND email IS NULL;
                UPDATE user_session SET revoked_at = now() WHERE revoked_at IS NULL;
            END LOOP;
            PERFORM set_config('app.tenant_id', '', true);
        END $$
        """
    )
    op.drop_column("user_account", "password_hash")

    op.add_column("user_session", sa.Column("idp_session_id", sa.String(255), nullable=True))
    op.add_column("user_session", sa.Column("refresh_token_encrypted", sa.Text(), nullable=True))
    op.add_column("user_session", sa.Column("id_token_encrypted", sa.Text(), nullable=True))
    op.add_column("user_session", sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_user_session_idp_session_id", "user_session", ["idp_session_id"])

    op.execute(f"DROP FUNCTION IF EXISTS {OLD_USER_LOOKUP}")
    op.execute(
        """
        CREATE FUNCTION saps_find_user_for_sign_in(p_issuer text, p_subject text, p_email text)
        RETURNS TABLE (user_id uuid, tenant_id uuid, idp_issuer text, idp_subject text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT u.id, u.tenant_id, u.idp_issuer, u.idp_subject FROM user_account u
            WHERE (u.idp_issuer = p_issuer AND u.idp_subject = p_subject)
               OR lower(u.email) = lower(p_email) OR lower(u.username) = lower(p_email)
            LIMIT 10
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION saps_find_idp_sessions(p_idp_session_id text)
        RETURNS TABLE (tenant_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT DISTINCT s.tenant_id FROM user_session s
            WHERE s.idp_session_id = p_idp_session_id AND s.revoked_at IS NULL
        $$
        """
    )
    for function in NEW_FUNCTIONS:
        _own(function)


def downgrade() -> None:
    for function in NEW_FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {function}")
    op.execute(
        """
        CREATE FUNCTION saps_find_user_for_sign_in(p_username text)
        RETURNS TABLE (user_id uuid, tenant_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT u.id, u.tenant_id FROM user_account u WHERE u.username = p_username LIMIT 1 $$
        """
    )
    _own(OLD_USER_LOOKUP)

    op.drop_index("ix_user_session_idp_session_id", table_name="user_session")
    for name in ("access_token_expires_at", "id_token_encrypted", "refresh_token_encrypted", "idp_session_id"):
        op.drop_column("user_session", name)
    # Passwords cannot come back: '!' matches no password; run the PoC seed again to set them.
    op.add_column(
        "user_account", sa.Column("password_hash", sa.String(255), nullable=False, server_default="!")
    )
    op.alter_column("user_account", "password_hash", server_default=None)
    op.drop_constraint("uq_user_account_idp_issuer_idp_subject", "user_account", type_="unique")
    for name in ("idp_subject", "idp_issuer", "email"):
        op.drop_column("user_account", name)
