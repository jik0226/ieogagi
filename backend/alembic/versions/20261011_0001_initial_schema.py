"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-11 16:32:31.433963
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("center_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=True),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("result", sa.String(length=10), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "result IN ('success', 'denied', 'failure')", name=op.f("ck_audit_log_result")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(
        "ix_audit_log_center_created", "audit_log", ["center_id", "created_at"], unique=False
    )
    op.create_table(
        "center",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_center")),
    )
    op.create_table(
        "app_user",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("center_id", sa.BigInteger(), nullable=False),
        sa.Column("login_id", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=30), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('director', 'staff', 'mentor')", name=op.f("ck_app_user_role")
        ),
        sa.CheckConstraint("failed_count >= 0", name=op.f("ck_app_user_failed_count")),
        sa.ForeignKeyConstraint(
            ["center_id"], ["center.id"], name=op.f("fk_app_user_center_id_center")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_user")),
        sa.UniqueConstraint("login_id", name=op.f("uq_app_user_login_id")),
    )
    op.create_index(op.f("ix_app_user_center_id"), "app_user", ["center_id"], unique=False)
    op.create_table(
        "child",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("center_id", sa.BigInteger(), nullable=False),
        sa.Column("alias", sa.String(length=20), nullable=False),
        sa.Column("grade", sa.String(length=4), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensitive_basis_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["center_id"], ["center.id"], name=op.f("fk_child_center_id_center")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["app_user.id"], name=op.f("fk_child_created_by_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_child")),
    )
    op.create_index(op.f("ix_child_center_id"), "child", ["center_id"], unique=False)
    op.create_table(
        "invite",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("center_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("role IN ('staff', 'mentor', 'director')", name=op.f("ck_invite_role")),
        sa.ForeignKeyConstraint(
            ["center_id"], ["center.id"], name=op.f("fk_invite_center_id_center")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["app_user.id"], name=op.f("fk_invite_created_by_app_user")
        ),
        sa.ForeignKeyConstraint(
            ["used_by"], ["app_user.id"], name=op.f("fk_invite_used_by_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invite")),
        sa.UniqueConstraint("code_hash", name=op.f("uq_invite_code_hash")),
    )
    op.create_index(op.f("ix_invite_center_id"), "invite", ["center_id"], unique=False)
    op.create_table(
        "user_session",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.id"], name=op.f("fk_user_session_user_id_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_session")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_session_token_hash")),
    )
    op.create_index(op.f("ix_user_session_user_id"), "user_session", ["user_id"], unique=False)
    op.create_table(
        "assignment",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("mentor_id", sa.BigInteger(), nullable=False),
        sa.Column("child_id", sa.BigInteger(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("start_date <= end_date", name=op.f("ck_assignment_period")),
        sa.ForeignKeyConstraint(
            ["child_id"], ["child.id"], name=op.f("fk_assignment_child_id_child")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["app_user.id"], name=op.f("fk_assignment_created_by_app_user")
        ),
        sa.ForeignKeyConstraint(
            ["mentor_id"], ["app_user.id"], name=op.f("fk_assignment_mentor_id_app_user")
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by"], ["app_user.id"], name=op.f("fk_assignment_revoked_by_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignment")),
    )
    op.create_index(op.f("ix_assignment_child_id"), "assignment", ["child_id"], unique=False)
    op.create_index(
        "ix_assignment_mentor_child", "assignment", ["mentor_id", "child_id"], unique=False
    )
    op.create_table(
        "record",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("child_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("did", sa.String(length=500), nullable=False),
        sa.Column("stuck", sa.String(length=500), nullable=False),
        sa.Column("next_step", sa.String(length=500), nullable=False),
        sa.Column("corrects_id", sa.BigInteger(), nullable=True),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hidden_by", sa.BigInteger(), nullable=True),
        sa.Column("hidden_reason_code", sa.String(length=20), nullable=True),
        sa.Column("redacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redacted_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "hidden_reason_code IS NULL OR hidden_reason_code IN "
            "('INAPPROPRIATE', 'WRONG_CHILD', 'DUPLICATE', 'SENSITIVE', 'OTHER')",
            name=op.f("ck_record_hidden_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["app_user.id"], name=op.f("fk_record_author_id_app_user")
        ),
        sa.ForeignKeyConstraint(["child_id"], ["child.id"], name=op.f("fk_record_child_id_child")),
        sa.ForeignKeyConstraint(
            ["corrects_id"], ["record.id"], name=op.f("fk_record_corrects_id_record")
        ),
        sa.ForeignKeyConstraint(
            ["hidden_by"], ["app_user.id"], name=op.f("fk_record_hidden_by_app_user")
        ),
        sa.ForeignKeyConstraint(
            ["redacted_by"], ["app_user.id"], name=op.f("fk_record_redacted_by_app_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record")),
        sa.UniqueConstraint("corrects_id", name=op.f("uq_record_corrects_id")),
    )
    op.create_index(op.f("ix_record_author_id"), "record", ["author_id"], unique=False)
    op.create_index("ix_record_child_session", "record", ["child_id", "session_date"], unique=False)
    op.create_table(
        "staff_note",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("child_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("nonce", sa.LargeBinary(), nullable=True),
        sa.Column("key_id", sa.String(length=20), nullable=True),
        sa.Column("share_text", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(ciphertext IS NULL AND nonce IS NULL AND key_id IS NULL) OR "
            "(ciphertext IS NOT NULL AND nonce IS NOT NULL AND key_id IS NOT NULL)",
            name=op.f("ck_staff_note_cipher_fields"),
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["app_user.id"], name=op.f("fk_staff_note_author_id_app_user")
        ),
        sa.ForeignKeyConstraint(
            ["child_id"], ["child.id"], name=op.f("fk_staff_note_child_id_child")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_note")),
    )
    op.create_index(op.f("ix_staff_note_child_id"), "staff_note", ["child_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_staff_note_child_id"), table_name="staff_note")
    op.drop_table("staff_note")
    op.drop_index("ix_record_child_session", table_name="record")
    op.drop_index(op.f("ix_record_author_id"), table_name="record")
    op.drop_table("record")
    op.drop_index("ix_assignment_mentor_child", table_name="assignment")
    op.drop_index(op.f("ix_assignment_child_id"), table_name="assignment")
    op.drop_table("assignment")
    op.drop_index(op.f("ix_user_session_user_id"), table_name="user_session")
    op.drop_table("user_session")
    op.drop_index(op.f("ix_invite_center_id"), table_name="invite")
    op.drop_table("invite")
    op.drop_index(op.f("ix_child_center_id"), table_name="child")
    op.drop_table("child")
    op.drop_index(op.f("ix_app_user_center_id"), table_name="app_user")
    op.drop_table("app_user")
    op.drop_table("center")
    op.drop_index("ix_audit_log_center_created", table_name="audit_log")
    op.drop_table("audit_log")
