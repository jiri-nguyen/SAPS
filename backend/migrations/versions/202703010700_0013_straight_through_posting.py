"""Straight-through posting to the ERP (SAPS-49, DEC-063, DEC-064, DEC-070).

Adds the ERP document and posting time to the invoice, the hold of a posting on a closed day, and the values an
accepted exception was accepted on. Invoices in Pending review (no final review any more) go to Posting once.

Revision ID: 0013
Revises: 0012
Create Date: 2027-03-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("invoice", sa.Column("erp_document_number", sa.String(50), nullable=True))
    op.add_column("invoice", sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoice", sa.Column("posting_held_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoice_exception", sa.Column("accepted_fingerprint", sa.String(64), nullable=True))
    # Pending review → Posting (SAPS-49 BR-10); the sweeper sends `post_invoice` once they are old enough.
    # The table owner is subject to FORCE ROW LEVEL SECURITY: work company by company under its own setting.
    op.execute(
        """
        DO $$
        DECLARE t uuid;
        BEGIN
            FOR t IN SELECT id FROM tenant LOOP
                PERFORM set_config('app.tenant_id', t::text, true);
                INSERT INTO invoice_event (id, tenant_id, invoice_id, status_from, status_to, action, actor,
                                           details, occurred_at, created_at, updated_at, created_by, updated_by)
                SELECT gen_random_uuid(), tenant_id, id, 'PENDING_REVIEW', 'POSTING', 'UPGRADE_TO_POSTING',
                       'system', NULL, now(), now(), now(), 'system', 'system'
                FROM invoice WHERE status = 'PENDING_REVIEW';
                UPDATE invoice SET status = 'POSTING', updated_at = now(), updated_by = 'system'
                WHERE status = 'PENDING_REVIEW';
            END LOOP;
            PERFORM set_config('app.tenant_id', '', true);
        END $$
        """
    )


def downgrade() -> None:
    # Count company by company: the table owner is subject to FORCE ROW LEVEL SECURITY.
    op.execute(
        """
        DO $$
        DECLARE t uuid; n bigint; total bigint := 0;
        BEGIN
            FOR t IN SELECT id FROM tenant LOOP
                PERFORM set_config('app.tenant_id', t::text, true);
                SELECT count(*) INTO n FROM invoice WHERE status IN ('POSTING', 'POSTED');
                total := total + n;
            END LOOP;
            PERFORM set_config('app.tenant_id', '', true);
            IF total > 0 THEN
                RAISE EXCEPTION '% invoice(s) are in Posting or Posted; the previous version cannot read them '
                    'and posted invoices cannot return to an earlier state', total;
            END IF;
        END $$
        """
    )
    op.drop_column("invoice_exception", "accepted_fingerprint")
    op.drop_column("invoice", "posting_held_at")
    op.drop_column("invoice", "posted_at")
    op.drop_column("invoice", "erp_document_number")
