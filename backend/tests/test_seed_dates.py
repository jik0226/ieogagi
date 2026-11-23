"""Demo seed: the story child keeps the poster's dates while the story still holds."""

from __future__ import annotations

from datetime import date

import pytest
from app.cli.seed_cmd import story_base
from app.cli.seed_data import STORY_ANCHOR


@pytest.mark.parametrize("today", [date(2026, 10, 18), date(2026, 10, 28), date(2026, 11, 19)])
def test_story_dates_match_the_poster_on_filming_and_booth_days(today: date) -> None:
    # 김하람 07.03 ~ 09.29 and 이도윤 09.30 ~ 12.20 come from offsets -100/-12, -11/70.
    assert story_base(today) == STORY_ANCHOR == date(2026, 10, 11)


@pytest.mark.parametrize("today", [date(2026, 10, 1), date(2026, 12, 21), date(2027, 3, 2)])
def test_story_falls_back_to_today_when_the_timeline_would_break(today: date) -> None:
    # Too early for the successor's weekly records, or after the successor's end date.
    assert story_base(today) == today
