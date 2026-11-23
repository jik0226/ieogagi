"""Test clock pinned to a given instant (test-only; production uses app.clock.Clock)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.clock import Clock


class FixedClock(Clock):
    """Clock pinned to a given instant."""

    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self.instant = instant

    def now(self) -> datetime:
        # Normalised to UTC like the real clock, so tests cannot mask a
        # missing Korea-time conversion.
        return self.instant.astimezone(UTC)

    def set(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self.instant = instant
