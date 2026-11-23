import { get, post } from './client.js';

const NO_REDIRECT = { skipUnauthorizedHandler: true };

// #1
export const verifyInvite = (code) => post('/auth/invites/verify', { code }, NO_REDIRECT);

// #2
export const signup = ({ code, login_id, display_name, password }) =>
  post('/auth/signup', { code, login_id, display_name, password }, NO_REDIRECT);

// #3
export const login = ({ login_id, password }) =>
  post('/auth/login', { login_id, password }, NO_REDIRECT);

// #4
export const logout = () => post('/auth/logout');

// #5 (the start-up check: "not signed in" is an expected answer here, so it
// must not trigger the "session expired" handling)
export const getMe = () => get('/auth/me', NO_REDIRECT);
