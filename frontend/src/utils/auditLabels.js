import { sensitiveCategoryLabels } from './labels.js';

// Korean glosses for the audit-log action codes. The code itself is always
// shown next to the gloss, because staff may search the log by code.
const ACTION_LABELS = new Map([
  ['auth.login', '로그인'],
  ['auth.logout', '로그아웃'],
  ['auth.signup', '가입'],
  ['invite.create', '초대 코드 발급'],
  ['user.disable', '계정 비활성화'],
  ['child.create', '아동 등록'],
  ['child.sensitive_basis', '민감정보 확인'],
  ['child.destroy', '아동 기록 파기'],
  ['assignment.create', '배정 만들기'],
  ['assignment.revoke', '배정 회수'],
  ['record.view', '기록 열람'],
  ['record.create', '기록 작성'],
  ['record.correct', '기록 정정'],
  ['record.hide', '기록 숨김'],
  ['record.redact', '칸 지우기'],
  ['record.sensitive_prompt', '민감어 확인 요청'],
  ['handover.view', '인계 카드 열람'],
  ['note.create', '메모 작성'],
  ['note.view', '메모 원문 열람'],
  ['audit.view', '감사 로그 조회'],
  ['access.denied', '접근 거부'],
]);

export const AUDIT_ACTIONS = [...ACTION_LABELS.keys()];

export function auditActionLabel(action) {
  return ACTION_LABELS.get(action) ?? '';
}

// Korean glosses for the codes inside `detail`. Reason codes keep the code in
// parentheses so staff can match them with the server log.
const DETAIL_KEY_LABELS = new Map([
  ['reason', '사유'],
  ['period', '배정 기간'],
  ['attempted', '시도'],
  ['assignment_id', '배정 ID'],
  ['child_id', '아동 ID'],
  ['mentor_id', '멘토 ID'],
  ['corrects_id', '정정 대상 기록 ID'],
  ['invite_id', '초대 ID'],
  ['role', '역할'],
  ['invite_role', '초대 역할'],
  ['categories', '민감어 분류'],
  ['sensitive_confirmed', '확인한 민감어'],
  ['sensitive_basis', '민감정보 확인'],
  ['fields', '지운 칸'],
  ['count', '건수'],
  ['records', '기록'],
  ['notes', '메모'],
  ['assignments', '배정'],
  ['has_body', '원문'],
  ['revoked_sessions', '끝낸 세션'],
  ['offset', '시작 위치'],
]);

const REASON_LABELS = new Map([
  ['not_assigned', '배정된 적 없는 아동'],
  ['before_start', '배정 시작 전 접근'],
  ['after_end', '배정 기간 종료 후 접근'],
  ['revoked', '회수된 배정'],
  ['role', '역할 권한 없음'],
  ['other_center_or_missing', '다른 센터 또는 없는 대상'],
  ['mentor_or_child_not_in_center', '다른 센터의 멘토·아동'],
  ['not_permitted_target', '다룰 수 없는 계정'],
  ['not_own_record_in_period', '기간 안의 본인 기록 아님'],
  ['unknown_account', '없는 아이디'],
  ['bad_password', '비밀번호 틀림'],
  ['locked', '잠긴 계정'],
  ['disabled', '비활성화된 계정'],
  ['invalid_invite', '잘못된 초대 코드'],
  ['issuer_disabled', '비활성화된 직원이 발급한 초대 코드'],
]);

// `attempted` is the route template (no real ids), shown as the screen action.
const ROUTE_LABELS = new Map([
  ['/api/children/{child_id}/handover-card', '인계 카드 열기'],
  ['/api/children/{child_id}/records', '기록 보기·쓰기'],
  ['/api/records/{record_id}/corrections', '기록 정정'],
  ['/api/records/{record_id}/hide', '기록 숨김'],
  ['/api/records/{record_id}/redact', '칸 지우기'],
  ['/api/children/{child_id}/notes', '메모 보기·쓰기'],
  ['/api/notes/{note_id}', '메모 원문 보기'],
  ['/api/children/{child_id}/sensitive-basis', '민감정보 확인'],
  ['/api/children/{child_id}', '아동 파기'],
  ['/api/children', '아동 목록·등록'],
  ['/api/assignments', '배정 목록·만들기'],
  ['/api/assignments/{assignment_id}/revoke', '배정 회수'],
  ['/api/users', '계정 목록'],
  ['/api/users/{user_id}/disable', '계정 비활성화'],
  ['/api/invites', '초대 코드 발급'],
  ['/api/audit-logs', '감사 로그 조회'],
  ['/api/me/assignments', '내 배정 목록'],
]);

// Record fields cleared by "칸 지우기" (detail.fields).
const FIELD_LABELS = new Map([
  ['did', '그날 한 것'],
  ['stuck', '막힌 곳'],
  ['next_step', '다음에 할 것'],
]);

function formatValue(key, value) {
  if (value === null || value === undefined) return '-';
  if (key === 'reason' && REASON_LABELS.has(value)) return `${REASON_LABELS.get(value)}(${value})`;
  if (key === 'attempted' && ROUTE_LABELS.has(value)) return ROUTE_LABELS.get(value);
  if (typeof value === 'boolean') return value ? '예' : '아니요';
  if (key === 'categories' || key === 'sensitive_confirmed') {
    const names = sensitiveCategoryLabels(value);
    return names.length > 0 ? names.join(', ') : '없음';
  }
  if (Array.isArray(value)) {
    const names = key === 'fields' ? value.map((field) => FIELD_LABELS.get(field) ?? field) : value;
    return names.length > 0 ? names.join(', ') : '없음';
  }
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

// The `detail` object as [label, value] pairs for the chips, e.g.
// ["사유", "배정 기간 종료 후 접근(after_end)"], ["배정 기간", "2026-06-01~2026-10-05"].
export function auditDetailEntries(detail) {
  if (!detail || typeof detail !== 'object') return [];
  return Object.entries(detail).map(([key, value]) => [
    DETAIL_KEY_LABELS.get(key) ?? key,
    formatValue(key, value),
  ]);
}

// "3 (김하람)" when the actor is known, "3" otherwise, "-" for no actor.
export function auditActorText(actorId, names) {
  if (actorId === null || actorId === undefined) return '-';
  const name = names.get(actorId);
  return name ? `${actorId} (${name})` : String(actorId);
}
