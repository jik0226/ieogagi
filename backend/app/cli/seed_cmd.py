"""``ieogagi-seed``: load fictional demo data (2 centers, 4 mentors, 12 children, 60 records).

Demo accounts share one password: ``IEOGAGI_SEED_PASSWORD`` if set (must pass
the password policy), otherwise a random one. The login list and, when
generated, the password are written to ``.secrets/seed_accounts.txt`` (0600).
"""

from __future__ import annotations

import argparse
import os
import secrets
from datetime import date, timedelta
from itertools import cycle

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cli.common import (
    out,
    owner_engine,
    resolve_output_path,
    setup_cli_logging,
    write_private_file,
)
from app.cli.seed_data import (
    CENTERS,
    EXTRA_RECORD_CHILDREN,
    GENERIC_RECORDS_PER_CHILD,
    GENERIC_SESSIONS,
    NOTE_BODIES,
    SHARE_TEXTS,
    STARLIGHT_SESSIONS,
    STORY_ANCHOR,
    STORY_CHILD,
    SUCCESSOR_SESSIONS,
)
from app.clock import Clock
from app.config import get_settings, load_secrets
from app.models import AppUser, Assignment, Base, Center, Child, Record, Role, StaffNote
from app.security.crypto import NoteKeyring, encrypt_note
from app.security.passwords import hash_password, password_policy_violation


def _password() -> tuple[str, bool]:
    configured = os.environ.get("IEOGAGI_SEED_PASSWORD", "")
    if configured:
        violation = password_policy_violation(configured)
        if violation:
            raise SystemExit(f"IEOGAGI_SEED_PASSWORD rejected: {violation}")
        return configured, False
    return secrets.token_urlsafe(12) + "aA1!", True


def story_base(today: date) -> date:
    """Day the story child's assignment offsets count from.

    STORY_ANCHOR keeps the poster's dates while the story still holds on ``today``:
    the predecessor's assignment has ended, and the successor's is in progress with
    room for its weekly records. Otherwise the offsets count from today as usual.
    """
    for spec in CENTERS:
        for alias, _login, start, end in spec["assignments"]:
            if alias != STORY_CHILD:
                continue
            first = STORY_ANCHOR + timedelta(days=start)
            last = STORY_ANCHOR + timedelta(days=end)
            if end < 0:
                holds = last < today
            else:
                earliest = first + timedelta(days=7 * len(SUCCESSOR_SESSIONS))
                holds = earliest <= today <= last
            if not holds:
                return today
    return STORY_ANCHOR


class Seeder:
    def __init__(self, db: Session, clock: Clock, keyring: NoteKeyring, password_hash: str):
        self.db = db
        self.now = clock.now()
        self.today = clock.today_kst()
        self.story_base = story_base(self.today)
        self.keyring = keyring
        self.password_hash = password_hash
        self.logins: list[str] = []
        self.generic = cycle(GENERIC_SESSIONS)

    def user(self, center: Center, login_id: str, name: str, role: Role) -> AppUser:
        user = AppUser(
            center_id=center.id,
            login_id=login_id,
            display_name=name,
            role=role.value,
            password_hash=self.password_hash,
            failed_count=0,
            created_at=self.now,
        )
        self.db.add(user)
        self.db.flush()
        self.logins.append(f"{login_id} ({role.value}, {center.name})")
        return user

    def record(self, child: Child, author: AppUser, day: date, content: tuple[str, str, str]):
        did, stuck, next_step = content
        self.db.add(
            Record(
                child_id=child.id,
                author_id=author.id,
                session_date=day,
                did=did,
                stuck=stuck,
                next_step=next_step,
                created_at=self.now,
            )
        )

    def weekly_records(self, child: Child, author: AppUser, last_day: date, contents) -> None:
        contents = list(contents)
        for index, content in enumerate(contents):
            self.record(
                child, author, last_day - timedelta(days=7 * (len(contents) - 1 - index)), content
            )

    def note(self, child: Child, staff: AppUser, share_text: str | None, body: str | None):
        note = StaffNote(
            child_id=child.id, author_id=staff.id, share_text=share_text, created_at=self.now
        )
        self.db.add(note)
        self.db.flush()
        if body:
            encrypted = encrypt_note(self.keyring, body, note_id=note.id, child_id=child.id)
            note.ciphertext, note.nonce, note.key_id = (
                encrypted.ciphertext,
                encrypted.nonce,
                encrypted.key_id,
            )

    def center(self, spec: dict) -> int:
        center = Center(name=spec["name"], created_at=self.now)
        self.db.add(center)
        self.db.flush()
        prefix = spec["prefix"]
        short = spec["name"][:2]
        self.user(center, f"{prefix}_director", f"{short} 센터장", Role.DIRECTOR)
        staff = self.user(center, f"{prefix}_staff", f"{short} 담당자", Role.STAFF)
        mentors = {
            login: self.user(center, login, name, Role.MENTOR) for login, name in spec["mentors"]
        }
        children = {}
        for alias, grade in spec["children"]:
            sensitive = self.now if alias in spec["sensitive_basis"] else None
            child = Child(
                center_id=center.id,
                alias=alias,
                grade=grade,
                consent_at=self.now,
                sensitive_basis_at=sensitive,
                created_by=staff.id,
                created_at=self.now,
            )
            self.db.add(child)
            self.db.flush()
            children[alias] = child
        records = 0
        for alias, login, start, end in spec["assignments"]:
            child, mentor = children[alias], mentors[login]
            base = self.story_base if alias == STORY_CHILD else self.today
            start_day, end_day = base + timedelta(days=start), base + timedelta(days=end)
            self.db.add(
                Assignment(
                    mentor_id=mentor.id,
                    child_id=child.id,
                    start_date=start_day,
                    end_date=end_day,
                    created_by=staff.id,
                    created_at=self.now,
                )
            )
            if start > 0:
                continue  # upcoming assignment: nothing written yet
            last_day = min(end_day, self.today - timedelta(days=1))
            if alias == "별빛":
                contents = STARLIGHT_SESSIONS if end < 0 else SUCCESSOR_SESSIONS
            else:
                count = GENERIC_RECORDS_PER_CHILD + (1 if alias in EXTRA_RECORD_CHILDREN else 0)
                contents = [next(self.generic) for _ in range(count)]
            self.weekly_records(child, mentor, last_day, contents)
            records += len(contents)
        for alias, texts in SHARE_TEXTS.items():
            for share_text in texts:
                if alias in children:
                    self.note(children[alias], staff, share_text, None)
        for alias, body in NOTE_BODIES.items():
            if alias in children:
                self.note(children[alias], staff, None, body)
        return records


def seed_command() -> None:
    parser = argparse.ArgumentParser(description="Load fictional demo data.")
    parser.add_argument("--reset", action="store_true", help="truncate all tables first")
    parser.add_argument("--accounts-file", default=".secrets/seed_accounts.txt")
    args = parser.parse_args()
    setup_cli_logging()
    accounts_file = resolve_output_path(args.accounts_file)

    settings = get_settings()
    if args.reset and settings.is_production:
        raise SystemExit("--reset is not allowed when IEOGAGI_ENV=production")
    password, generated = _password()
    engine = owner_engine()
    with Session(engine) as db:
        if args.reset:
            # Children before parents; plain DELETE statements, no raw SQL.
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            # Restart id sequences so demo ids are stable (e.g. 별빛 is always child 1).
            for table in Base.metadata.sorted_tables:
                sequence = func.pg_get_serial_sequence(table.name, "id")
                db.execute(select(func.setval(sequence, 1, False)))
        elif db.scalar(select(Center.id).limit(1)) is not None:
            raise SystemExit("Database already has data; use --reset (development only).")
        seeder = Seeder(db, Clock(), load_secrets(settings).keyring, hash_password(password))
        total = sum(seeder.center(spec) for spec in CENTERS)
        db.commit()
    engine.dispose()
    lines = ["# Demo accounts (fictional data only)", *seeder.logins]
    lines.append(f"password: {password}" if generated else "password: IEOGAGI_SEED_PASSWORD")
    write_private_file(accounts_file, "\n".join(lines))
    out(f"Seeded {len(CENTERS)} centers, {len(seeder.logins)} accounts, {total} records.")
    out(f"Account list written to {args.accounts_file} (mode 0600).")
