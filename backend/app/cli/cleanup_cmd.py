"""``ieogagi-cleanup``: delete expired/revoked sessions and used/expired invites.

Rows are removed once they have been dead for more than the retention window
(30 days by default, never less). Login, logout, signup and invite facts are
already in ``audit_log``. The application database role has no DELETE on these
tables by design, so the command runs as the owner role, like the other admin
commands.
"""

from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.cli.common import out, owner_engine, setup_cli_logging
from app.clock import Clock
from app.config import get_settings
from app.services.retention import MAX_RETENTION_DAYS, MIN_RETENTION_DAYS, purge_stale_rows


def _retention_days(raw: str) -> int:
    """argparse type: an integer within the allowed retention range."""
    try:
        days = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not an integer: {raw!r}") from exc
    if not MIN_RETENTION_DAYS <= days <= MAX_RETENTION_DAYS:
        raise argparse.ArgumentTypeError(
            f"must be between {MIN_RETENTION_DAYS} and {MAX_RETENTION_DAYS}"
        )
    return days


def cleanup_command() -> None:
    parser = argparse.ArgumentParser(
        description="Delete expired/revoked sessions and used/expired invites past retention."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="count the rows that would be deleted, delete none"
    )
    parser.add_argument(
        "--days",
        type=_retention_days,
        default=MIN_RETENTION_DAYS,
        help=f"retention window in days (default and minimum: {MIN_RETENTION_DAYS})",
    )
    args = parser.parse_args()
    setup_cli_logging()

    now = Clock().now()
    idle_minutes = get_settings().session_idle_minutes
    engine = owner_engine()
    try:
        with Session(engine) as db:
            result = purge_stale_rows(
                db, now, retention_days=args.days, idle_minutes=idle_minutes, dry_run=args.dry_run
            )
            if not args.dry_run:
                db.commit()
    finally:
        engine.dispose()
    verb = "Dry run: would delete" if args.dry_run else "Deleted"
    out(
        f"{verb} {result.sessions} sessions and {result.invites} invites "
        f"older than {args.days} days"
    )
