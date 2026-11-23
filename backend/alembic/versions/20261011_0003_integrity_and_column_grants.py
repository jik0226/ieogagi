"""Integrity constraints and column-level grants (from the 2026-10-11 security review).

1. No overlapping live assignments for the same mentor and child (exclusion
   constraint), so revoking one assignment always closes access.
2. Only a visible correction supersedes a record: a hidden correction no
   longer freezes the chain (partial unique index instead of UNIQUE).
3. Destroying a child detaches its assignments (child_id -> NULL) instead of
   deleting them, keeping the "assignment ended" signal for account cleanup.
4. The application role may UPDATE only the columns its code paths change;
   identity and ownership columns (role, center_id, author_id, child_id of
   records, dates of assignments, ...) are immutable from the application.

All statements are constant SQL text (no interpolation).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        "ALTER TABLE assignment ADD CONSTRAINT ex_assignment_no_overlap "
        "EXCLUDE USING gist (mentor_id WITH =, child_id WITH =, "
        "daterange(start_date, end_date, '[]') WITH &&) WHERE (revoked_at IS NULL)"
    )
    op.execute("ALTER TABLE assignment ALTER COLUMN child_id DROP NOT NULL")

    op.execute("ALTER TABLE record DROP CONSTRAINT uq_record_corrects_id")
    op.execute(
        "CREATE UNIQUE INDEX uq_record_corrects_id_visible ON record (corrects_id) "
        "WHERE hidden_at IS NULL"
    )

    op.execute(
        "REVOKE UPDATE ON app_user, user_session, invite, child, assignment, record, staff_note "
        "FROM ieogagi_app"
    )
    op.execute(
        "GRANT UPDATE (failed_count, locked_until, disabled_at, password_hash) "
        "ON app_user TO ieogagi_app"
    )
    op.execute("GRANT UPDATE (last_seen_at, revoked_at) ON user_session TO ieogagi_app")
    op.execute("GRANT UPDATE (used_at, used_by) ON invite TO ieogagi_app")
    op.execute("GRANT UPDATE (sensitive_basis_at) ON child TO ieogagi_app")
    op.execute("GRANT UPDATE (revoked_at, revoked_by, child_id) ON assignment TO ieogagi_app")
    op.execute(
        "GRANT UPDATE (did, stuck, next_step, hidden_at, hidden_by, hidden_reason_code, "
        "redacted_at, redacted_by) ON record TO ieogagi_app"
    )
    op.execute("GRANT UPDATE (ciphertext, nonce, key_id) ON staff_note TO ieogagi_app")


def downgrade() -> None:
    op.execute(
        "REVOKE UPDATE ON app_user, user_session, invite, child, assignment, record, staff_note "
        "FROM ieogagi_app"
    )
    op.execute("GRANT UPDATE ON app_user, user_session, invite TO ieogagi_app")
    op.execute("GRANT UPDATE ON child, assignment, record, staff_note TO ieogagi_app")
    op.execute("DROP INDEX uq_record_corrects_id_visible")
    op.execute("ALTER TABLE record ADD CONSTRAINT uq_record_corrects_id UNIQUE (corrects_id)")
    op.execute("ALTER TABLE assignment ALTER COLUMN child_id SET NOT NULL")
    op.execute("ALTER TABLE assignment DROP CONSTRAINT ex_assignment_no_overlap")
