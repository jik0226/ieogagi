"""Time source.

"Today" for assignment checks is always the Korea date computed in the
application and passed to SQL as a bound parameter. The database's
CURRENT_DATE is never used, so server/DB timezone settings cannot shift the
access window. The clock is injectable so tests can pin exact boundary times.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, Request

KST = ZoneInfo("Asia/Seoul")


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def today_kst(self) -> date:
        return self.now().astimezone(KST).date()


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


ClockDep = Annotated[Clock, Depends(get_clock)]
