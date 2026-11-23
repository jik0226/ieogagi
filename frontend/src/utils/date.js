// All dates in the contract are Korean (KST) calendar dates: YYYY-MM-DD.
const KST = 'Asia/Seoul';

const dateFormatter = new Intl.DateTimeFormat('sv-SE', { timeZone: KST });

const dateTimeFormatter = new Intl.DateTimeFormat('ko-KR', {
  timeZone: KST,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export function todayKst(now = new Date()) {
  return dateFormatter.format(now);
}

export function isDateString(value) {
  return typeof value === 'string' && DATE_PATTERN.test(value);
}

export function formatDate(value) {
  return isDateString(value) ? value.replaceAll('-', '.') : '-';
}

export function formatPeriod(start, end) {
  return `${formatDate(start)} ~ ${formatDate(end)}`;
}

// Timestamps arrive as UTC ISO 8601 and are shown in KST.
export function formatDateTime(iso) {
  if (typeof iso !== 'string') return '-';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '-';
  const parts = Object.fromEntries(
    dateTimeFormatter.formatToParts(date).map((part) => [part.type, part.value]),
  );
  return `${parts.year}.${parts.month}.${parts.day} ${parts.hour}:${parts.minute}`;
}

// Timestamp shown as a Korean calendar date only, e.g. "2026.10.11".
export function formatDateOnly(iso) {
  if (typeof iso !== 'string') return '-';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '-';
  return formatDate(dateFormatter.format(date));
}

function toUtcMs(dateString) {
  const [year, month, day] = dateString.split('-').map(Number);
  return Date.UTC(year, month - 1, day);
}

export function addDays(dateString, days) {
  const moved = new Date(toUtcMs(dateString) + days * 86400000);
  return moved.toISOString().slice(0, 10);
}

export function diffDays(from, to) {
  return Math.round((toUtcMs(to) - toUtcMs(from)) / 86400000);
}
