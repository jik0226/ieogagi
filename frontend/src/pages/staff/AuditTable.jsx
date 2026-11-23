import Badge from '../../components/Badge.jsx';
import ScrollTable from '../../components/ScrollTable.jsx';
import { auditActionLabel, auditDetailEntries } from '../../utils/auditLabels.js';
import { formatDate, formatDateTime, todayKst } from '../../utils/date.js';
import { auditResult } from '../../utils/labels.js';

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
const AVATAR_TONES = ['peach', 'sage', 'butter'];

// Colour + icon per kind of action. The Korean label is always printed next
// to it, so the tile is decoration only.
const ACTION_KINDS = new Map([
  ['auth', 'enter'],
  ['record', 'doc'],
  ['handover', 'doc'],
  ['note', 'doc'],
  ['child', 'people'],
  ['assignment', 'people'],
  ['user', 'people'],
  ['invite', 'people'],
  ['audit', 'eye'],
  ['access', 'stop'],
]);

function ActionIcon({ kind }) {
  return (
    <svg className="audit-action__icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
      {kind === 'enter' && <path d="M10 17l5-5-5-5M15 12H3M14 4h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-5" />}
      {kind === 'doc' && <path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6" />}
      {kind === 'people' && <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 4-6 8-6s8 2 8 6" />}
      {kind === 'eye' && <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />}
      {kind === 'stop' && <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM5.6 5.6l12.8 12.8" />}
    </svg>
  );
}

function splitDateTime(iso) {
  const text = formatDateTime(iso);
  const [day = '-', time = '-'] = text.split(' ');
  return { day, time };
}

// "2026.10.28 (수) · 오늘"
function dayLabel(day) {
  const [year, month, date] = day.split('.').map(Number);
  if (!year || !month || !date) return day;
  const weekday = WEEKDAYS.at(new Date(Date.UTC(year, month - 1, date)).getUTCDay());
  const today = day === formatDate(todayKst()) ? ' · 오늘' : '';
  return `${day} (${weekday})${today}`;
}

function targetText(log) {
  if (!log.target_type) return '-';
  return log.target_id === null ? log.target_type : `${log.target_type} #${log.target_id}`;
}

function Actor({ actorId, names }) {
  if (actorId === null || actorId === undefined) return '-';
  const name = names.get(actorId);
  const tone = AVATAR_TONES.at(Number(actorId) % AVATAR_TONES.length);
  return (
    <span className="audit-actor">
      <span className={`audit-avatar audit-avatar--${tone}`} aria-hidden="true">
        {name ? name.slice(0, 1) : '#'}
      </span>
      {/* An account missing from the list is shown by its ID alone, not as a
          "알 수 없음" that reads like a broken row. */}
      <span className="audit-actor__text">
        <span className="audit-actor__name">{name ?? `ID ${actorId}`}</span>
        {name && <span className="audit-actor__id">ID {actorId}</span>}
      </span>
    </span>
  );
}

function Detail({ detail }) {
  const entries = auditDetailEntries(detail);
  if (entries.length === 0) return '-';
  return (
    <span className="audit-chips">
      {entries.map(([key, value]) => (
        <span key={key} className="audit-chip">
          <span className="audit-chip__key">{key}</span> {value}
        </span>
      ))}
    </span>
  );
}

// Rows are grouped by day. Denied rows get a tinted row, a red edge and a
// "거부" badge, so they stand out without relying on colour alone.
export default function AuditTable({ items, actorNames }) {
  const rows = [];
  let lastDay = null;
  for (const log of items) {
    const { day, time } = splitDateTime(log.created_at);
    if (day !== lastDay) {
      lastDay = day;
      rows.push(
        <tr key={`day-${day}-${log.id}`} className="audit-day">
          <th scope="colgroup" colSpan={7}>
            <span className="audit-day__label">{dayLabel(day)}</span>
          </th>
        </tr>,
      );
    }
    const result = auditResult(log.result);
    const gloss = auditActionLabel(log.action);
    const kind = ACTION_KINDS.get(log.action.split('.')[0]) ?? 'doc';
    rows.push(
      <tr key={log.id} className={log.result === 'success' ? undefined : 'is-denied'}>
        <td className="table__nowrap">
          <time className="audit-time" dateTime={log.created_at}>
            {time}
          </time>
        </td>
        <td>
          <Actor actorId={log.actor_id} names={actorNames} />
        </td>
        <td>
          <span className="audit-action">
            <span className={`audit-action__tile audit-action__tile--${kind}`}>
              <ActionIcon kind={kind} />
            </span>
            <span className="audit-action__text">
              <span className="audit-action__label">{gloss || log.action}</span>
              <span className="table__mono audit-action__code">{log.action}</span>
            </span>
          </span>
        </td>
        <td>{targetText(log)}</td>
        <td>
          <Badge tone={result.tone}>{result.label}</Badge>
        </td>
        <td className="table__mono audit-ip">{log.ip ?? '-'}</td>
        <td className="table__detail">
          <Detail detail={log.detail} />
        </td>
      </tr>,
    );
  }

  return (
    <ScrollTable label="감사 로그 표">
      <table className="table table--wide audit-table">
        <thead>
          <tr>
            <th scope="col">시각</th>
            <th scope="col">행위자</th>
            <th scope="col">동작</th>
            <th scope="col">대상</th>
            <th scope="col">결과</th>
            <th scope="col">IP</th>
            <th scope="col">상세</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </ScrollTable>
  );
}
