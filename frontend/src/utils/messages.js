import { ApiError } from '../api/client.js';

// One fixed wording for every 403: the reason (period over, revoked, other
// centre, wrong role) is never spelled out on screen.
export const FORBIDDEN_TITLE = '열람 기간이 아니거나 권한이 없습니다';
export const FORBIDDEN_TEXT =
  '배정 기간이 끝났거나 회수된 아동의 기록은 볼 수 없습니다. 필요하면 담당 선생님께 문의하세요.';
export const FORBIDDEN_MESSAGE = `${FORBIDDEN_TITLE}.`;
export const SESSION_EXPIRED_MESSAGE = '세션이 만료되었습니다. 다시 로그인해 주세요.';
export const ALREADY_CORRECTED_MESSAGE = '이미 정정된 기록입니다. 최신 기록을 정정해 주세요.';

// Login failures keep one wording for every cause (unknown id, wrong password,
// locked); only the next step is added on screen.
const LOGIN_FAILED_HELP = '계속 안 되면 담당 선생님께 문의해 주세요.';
const RATE_LIMITED_MESSAGE = '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
const GENERIC_MESSAGE = '요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';

// Turns any thrown value into text that is safe to show. Only the server's
// own `message` field is shown; unexpected errors never leak their details.
export function describeError(error) {
  if (!(error instanceof ApiError)) return GENERIC_MESSAGE;
  if (error.status === 403) return FORBIDDEN_MESSAGE;
  if (error.status === 429) return error.message || RATE_LIMITED_MESSAGE;
  if (error.code === 'LOGIN_FAILED') return `${error.message} ${LOGIN_FAILED_HELP}`;
  return error.message || GENERIC_MESSAGE;
}

// Last segment of each path in a 422 `fields` array, e.g. "body.did" -> "did".
export function invalidFieldNames(error) {
  if (!(error instanceof ApiError) || error.code !== 'VALIDATION_FAILED') {
    return new Set();
  }
  const names = error.fields.map((path) => {
    const parts = Array.isArray(path) ? path : String(path).split('.');
    return String(parts.at(-1));
  });
  return new Set(names);
}

export function isStatus(error, status) {
  return error instanceof ApiError && error.status === status;
}
