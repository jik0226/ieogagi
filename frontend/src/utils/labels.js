// Display labels for contract enums. Maps are used so unknown values never
// resolve through object property lookup.
const ROLE_LABELS = new Map([
  ['director', '시설장'],
  ['staff', '담당자'],
  ['mentor', '멘토'],
]);

// "…(으)로 초대되었습니다" sentences need the particle with the role name.
const INVITE_ROLE_LABELS = new Map([
  ['director', '시설장으로'],
  ['staff', '담당자로'],
  ['mentor', '멘토로'],
]);

const ASSIGNMENT_STATUS = new Map([
  ['upcoming', { label: '시작 전', tone: 'info' }],
  ['active', { label: '진행 중', tone: 'success' }],
  ['ended', { label: '종료', tone: 'neutral' }],
  ['revoked', { label: '회수됨', tone: 'danger' }],
]);

const AUDIT_RESULT = new Map([
  ['success', { label: '성공', tone: 'success' }],
  ['denied', { label: '거부', tone: 'danger' }],
  ['failure', { label: '실패', tone: 'danger' }],
]);

const HIDE_REASONS = [
  { value: 'INAPPROPRIATE', label: '부적절한 내용' },
  { value: 'WRONG_CHILD', label: '다른 아동 기록' },
  { value: 'DUPLICATE', label: '중복' },
  { value: 'SENSITIVE', label: '민감정보' },
  { value: 'OTHER', label: '기타' },
];

const SENSITIVE_CATEGORIES = new Map([
  ['health', '건강'],
  ['family', '가정'],
]);

export const GRADES = [
  '초1', '초2', '초3', '초4', '초5', '초6',
  '중1', '중2', '중3',
  '고1', '고2', '고3',
];

// Pairs each record field with its value; avoids dynamic property lookups.
// `past`: a saved record of an earlier session, so "오늘 한 것" reads as
// "그날 한 것" and is not mistaken for today's plan. Only the input form
// keeps "오늘 한 것".
export function recordFieldEntries(record, { past = false } = {}) {
  return [
    { name: 'did', label: past ? '그날 한 것' : '오늘 한 것', value: record.did ?? '' },
    { name: 'stuck', label: '막힌 곳', value: record.stuck ?? '' },
    { name: 'next_step', label: '다음에 할 것', value: record.next_step ?? '' },
  ];
}

export const AUDIT_RESULTS = ['success', 'denied', 'failure'];

export const HIDE_REASON_OPTIONS = HIDE_REASONS;

export function roleLabel(role) {
  return ROLE_LABELS.get(role) ?? '알 수 없음';
}

export function inviteRoleLabel(role) {
  return INVITE_ROLE_LABELS.get(role) ?? '알 수 없는 역할로';
}

export function assignmentStatus(status) {
  return ASSIGNMENT_STATUS.get(status) ?? { label: '알 수 없음', tone: 'neutral' };
}

export function auditResult(result) {
  return AUDIT_RESULT.get(result) ?? { label: '알 수 없음', tone: 'neutral' };
}

export function hideReasonLabel(code) {
  const found = HIDE_REASONS.find((reason) => reason.value === code);
  return found ? found.label : '사유 없음';
}

export function sensitiveCategoryLabels(categories) {
  const list = Array.isArray(categories) ? categories : [];
  return list.map((category) => SENSITIVE_CATEGORIES.get(category) ?? '기타');
}
