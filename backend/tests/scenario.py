"""A shared scenario mirroring Figure 2 of the plan.

Center A has a previous mentor (2026-06-01~10-05) and a current mentor
(2026-10-06~12-20) for child 별빛; center B is a separate center.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.clock import KST
from app.models import AppUser, Assignment, Center, Child, Record, Role

from tests.factories import Factory

START = date(2026, 10, 6)
END = date(2026, 12, 20)
PREV_START = date(2026, 6, 1)
PREV_END = date(2026, 10, 5)


def kst(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=KST)


@dataclass
class World:
    center_a: Center
    center_b: Center
    director_a: AppUser
    staff_a: AppUser
    staff_a2: AppUser
    mentor_prev: AppUser
    mentor_now: AppUser
    mentor_other: AppUser
    director_b: AppUser
    staff_b: AppUser
    mentor_b: AppUser
    child: Child
    child_b: Child
    assignment_now: Assignment
    prior_records: list[Record]


def build_world(f: Factory) -> World:
    center_a = f.center("햇살지역아동센터")
    center_b = f.center("달빛지역아동센터")
    director_a = f.user(center_a, Role.DIRECTOR)
    staff_a = f.user(center_a, Role.STAFF)
    staff_a2 = f.user(center_a, Role.STAFF)
    mentor_prev = f.user(center_a, Role.MENTOR, name="이전멘토")
    mentor_now = f.user(center_a, Role.MENTOR, name="현재멘토")
    mentor_other = f.user(center_a, Role.MENTOR)
    director_b = f.user(center_b, Role.DIRECTOR)
    staff_b = f.user(center_b, Role.STAFF)
    mentor_b = f.user(center_b, Role.MENTOR)
    child = f.child(center_a, staff_a)
    child_b = f.child(center_b, staff_b, alias="해님")
    f.assignment(mentor_prev, child, PREV_START, PREV_END, staff_a)
    assignment_now = f.assignment(mentor_now, child, START, END, staff_a)
    f.assignment(mentor_b, child_b, START, END, staff_b)
    session_days = [
        date(2026, 9, 1),
        date(2026, 9, 8),
        date(2026, 9, 15),
        date(2026, 9, 22),
        date(2026, 9, 29),
        date(2026, 10, 5),
    ]
    prior = [
        f.record(child, mentor_prev, day, did=f"{number}회 수업")
        for number, day in enumerate(session_days, start=1)
    ]
    return World(
        center_a=center_a,
        center_b=center_b,
        director_a=director_a,
        staff_a=staff_a,
        staff_a2=staff_a2,
        mentor_prev=mentor_prev,
        mentor_now=mentor_now,
        mentor_other=mentor_other,
        director_b=director_b,
        staff_b=staff_b,
        mentor_b=mentor_b,
        child=child,
        child_b=child_b,
        assignment_now=assignment_now,
        prior_records=prior,
    )
