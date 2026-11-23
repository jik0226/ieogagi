// Single fetch wrapper for every API call. The session lives in an HttpOnly
// cookie, so this code never reads, stores or forwards a token.
const API_BASE = '/api';

const GENERIC_MESSAGE = '요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.';
const NETWORK_MESSAGE = '서버에 연결하지 못했습니다. 네트워크 상태를 확인해 주세요.';
// A 2xx answer whose body could not be read: the change may or may not have
// happened, so the user is asked to check before trying again.
const INVALID_RESPONSE_MESSAGE =
  '처리 결과를 확인하지 못했습니다. 목록에서 반영됐는지 확인한 뒤 다시 시도해 주세요.';
const UNREADABLE = Symbol('unreadable-body');

export class ApiError extends Error {
  constructor({ status, code, message, fields, categories, hasServerMessage = false }) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    // True when `message` is the server's own wording, not our fallback.
    this.hasServerMessage = hasServerMessage;
    this.fields = Array.isArray(fields) ? fields : [];
    this.categories = Array.isArray(categories) ? categories : [];
  }
}

let unauthorizedHandler = null;

// The auth provider registers a callback here; it runs on every 401 except
// for calls that opt out (login, invite checks).
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
}

// Path parameters are numeric ids; encode them anyway so a bad value can
// never change the shape of the URL.
export function segment(value) {
  return encodeURIComponent(String(value));
}

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  });
  const text = search.toString();
  return text ? `?${text}` : '';
}

// Returns the parsed body, or UNREADABLE when it is missing or not JSON.
async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return UNREADABLE;
  }
}

function toApiError(status, payload) {
  const body = payload && typeof payload === 'object' ? payload.error : null;
  const hasServerMessage = Boolean(body && typeof body.message === 'string' && body.message);
  const message = hasServerMessage ? body.message : GENERIC_MESSAGE;
  return new ApiError({
    status,
    code: body && typeof body.code === 'string' ? body.code : 'UNKNOWN',
    message,
    hasServerMessage,
    fields: body?.fields,
    categories: body?.categories,
  });
}

export async function request(method, path, options = {}) {
  const { body, query, skipUnauthorizedHandler = false } = options;
  const headers = { Accept: 'application/json' };
  const init = { method, credentials: 'same-origin', headers };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}${buildQuery(query)}`, init);
  } catch {
    throw new ApiError({ status: 0, code: 'NETWORK_ERROR', message: NETWORK_MESSAGE });
  }

  // By contract only #4 (log-out) and #12 (child destroy) answer 204 with no
  // body. Every other success must carry JSON; anything else is an error so a
  // failed or garbled answer is never treated as a success.
  if (response.status === 204) return null;

  const payload = await readJson(response);
  if (response.ok) {
    if (payload === UNREADABLE || payload === null) {
      throw new ApiError({
        status: response.status,
        code: 'INVALID_RESPONSE',
        message: INVALID_RESPONSE_MESSAGE,
      });
    }
    return payload;
  }

  const error = toApiError(response.status, payload === UNREADABLE ? null : payload);
  if (response.status === 401 && !skipUnauthorizedHandler && unauthorizedHandler) {
    unauthorizedHandler(error);
  }
  throw error;
}

export const get = (path, options) => request('GET', path, options);
export const post = (path, body, options) => request('POST', path, { ...options, body });
export const del = (path, options) => request('DELETE', path, options);
