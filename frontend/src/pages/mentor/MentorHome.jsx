import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import { listMyAssignments } from '../../api/assignments.js';
import AsyncView from '../../components/AsyncView.jsx';
import Badge from '../../components/Badge.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { useAuth } from '../../auth/useAuth.js';
import { useAsync } from '../../hooks/useAsync.js';
import { diffDays, formatPeriod, todayKst } from '../../utils/date.js';
import { assignmentStatus } from '../../utils/labels.js';

// How far into the assignment period today is. Dates come from the card
// itself, so nothing extra is requested. `left` is days until the end date.
function periodProgress(start, end, today) {
  const total = Math.max(diffDays(start, end), 1);
  const passed = Math.min(Math.max(diffDays(start, today), 0), total);
  return { total, passed, percent: Math.round((passed / total) * 100), left: diffDays(today, end) };
}

// D-day counts down to the END of the assignment. The end date itself is
// "오늘 종료" (never a negative number); after it the card reads "종료됨".
function daysLeftLabel(left) {
  if (left > 0) return `종료까지 D-${left}`;
  return left === 0 ? '오늘 종료 · D-day' : '종료됨';
}

// Days until an assignment that has not started yet begins.
function startsInLabel(until) {
  return until > 0 ? `시작까지 D-${until}` : '오늘 시작';
}

// The status from the API is not enough on its own: a list loaded before
// midnight still says "active" on the day after the end date.
function phaseOf(item, today) {
  if (item.end_date < today) return 'ended';
  return item.status === 'upcoming' ? 'upcoming' : 'active';
}

// "2026-09-30" -> "09.30" (the year is in the full period on the hand-over page).
function shortDate(value) {
  return value.slice(5).replace('-', '.');
}

// Only "active" cards open the hand-over card. "upcoming" and ended cards are
// dashed, grey and not clickable, so no request is sent that would be refused.
// Only a running assignment shows a progress bar.
function AssignmentCard({ item, today }) {
  const phase = phaseOf(item, today);
  const status = assignmentStatus(item.status);
  const open = phase === 'active';
  const period = formatPeriod(item.start_date, item.end_date);
  // Tile colours rotate peach / sage / butter by position in the list.
  const progress = open ? periodProgress(item.start_date, item.end_date, today) : null;

  const body = (
    <article className={open ? 'card assignment-card' : 'card card--upcoming assignment-card'}>
      <span className="assignment-card__tile" aria-hidden="true">
        {item.child.alias.slice(0, 1)}
      </span>
      <div className="assignment-card__body">
        <div className="assignment-card__head">
          <h2>{item.child.alias}</h2>
          <span className="meta">{item.child.grade}</span>
          {phase === 'upcoming' && <Badge tone={status.tone}>{status.label}</Badge>}
          {phase === 'ended' && <Badge>종료됨</Badge>}
        </div>
        {open && (
          <>
            <div className="assignment-card__status">
              <Badge tone={status.tone}>{status.label}</Badge>
              <span className="badge badge--dday">{daysLeftLabel(progress.left)}</span>
            </div>
            <progress
              className="period-bar"
              max={progress.total}
              value={progress.passed}
              aria-label={`배정 기간 ${progress.percent}% 지남`}
            />
            <p className="meta">
              {shortDate(item.start_date)} ~ {shortDate(item.end_date)} · {progress.percent}% 지남
            </p>
            <span className="assignment-card__chevron">
              <span className="visually-hidden">인계 카드 보기</span>
              <span aria-hidden="true">›</span>
            </span>
          </>
        )}
        {phase === 'upcoming' && (
          <>
            <div className="assignment-card__status">
              <span className="badge badge--dday">{startsInLabel(diffDays(today, item.start_date))}</span>
            </div>
            <p className="meta">{period}</p>
            <p className="assignment-card__note">시작일부터 인계 카드와 기록을 볼 수 있습니다.</p>
          </>
        )}
        {phase === 'ended' && (
          <>
            <p className="meta">{period}</p>
            <p className="assignment-card__note">배정 기간이 끝나 인계 카드와 기록을 볼 수 없습니다.</p>
          </>
        )}
      </div>
    </article>
  );

  if (!open) return body;
  return (
    <Link className="card-link" to={`/mentor/children/${item.child.id}`}>
      {body}
    </Link>
  );
}

// The API already leaves out ended and revoked assignments; the filter keeps
// them off the screen even if that ever changed. Running assignments come
// first (newest start first), then the ones that have not started (soonest
// start first), then any that ended since the list was loaded.
const PHASE_ORDER = new Map([
  ['active', 0],
  ['upcoming', 1],
  ['ended', 2],
]);

function visibleSorted(items, today) {
  return items
    .filter((item) => item.status === 'active' || item.status === 'upcoming')
    .map((item) => ({ item, phase: phaseOf(item, today) }))
    .sort((a, b) => {
      if (a.phase !== b.phase) return PHASE_ORDER.get(a.phase) - PHASE_ORDER.get(b.phase);
      const byStart = a.item.start_date.localeCompare(b.item.start_date);
      return a.phase === 'upcoming' ? byStart : -byStart;
    })
    .map(({ item }) => item);
}

export default function MentorHome() {
  const load = useCallback(() => listMyAssignments(), []);
  const { loading, data, error, reload } = useAsync(load);
  const today = todayKst();
  const items = data ? visibleSorted(data, today) : [];
  const { user } = useAuth();

  return (
    <div className="stack">
      <section className="mentor-hero" aria-label="인사">
        <p className="mentor-hero__hello">안녕하세요,</p>
        <p className="mentor-hero__name">{user.display_name} 선생님!</p>
        <p className="mentor-hero__where">{user.center.name} · 멘토</p>
      </section>
      <h1>내 아동</h1>
      <AsyncView loading={loading} error={error} onRetry={reload} screen>
        {items.length === 0 ? (
          <EmptyState boxed title="배정된 아동이 없습니다.">
            배정 기간이 끝났거나 아직 배정되지 않았습니다. 담당 선생님께 문의하세요.
          </EmptyState>
        ) : (
          <ul className="card-list">
            {items.map((item) => (
              <li key={item.assignment_id}>
                <AssignmentCard item={item} today={today} />
              </li>
            ))}
          </ul>
        )}
      </AsyncView>
    </div>
  );
}
