"""Least-privilege grants for the application role.

The schema belongs to the owner role (runs migrations). The application
connects as ``ieogagi_app`` and gets only what its code paths need:
- audit_log: SELECT, INSERT only -> no application path can alter or erase audit history
- center: SELECT only (centers are added with the owner-side admin command)
- app_user, user_session, invite: no DELETE (accounts are disabled, sessions revoked)
- child, assignment, record, staff_note: DELETE allowed for the director's destruction

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA public TO ieogagi_app")
    op.execute("GRANT SELECT ON center TO ieogagi_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON app_user, user_session, invite TO ieogagi_app")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON child, assignment, record, staff_note "
        "TO ieogagi_app"
    )
    op.execute("GRANT SELECT, INSERT ON audit_log TO ieogagi_app")
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ieogagi_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM ieogagi_app")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM ieogagi_app")
    op.execute("REVOKE USAGE ON SCHEMA public FROM ieogagi_app")
