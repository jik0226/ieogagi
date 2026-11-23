"""Revoke the application's unused DELETE privilege on assignment.

Since 0003, destroying a child detaches its assignments (UPDATE child_id,
revoked_at) instead of deleting them, so the app role no longer needs DELETE.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE DELETE ON assignment FROM ieogagi_app")


def downgrade() -> None:
    op.execute("GRANT DELETE ON assignment TO ieogagi_app")
