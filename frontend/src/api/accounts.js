import { get, post, segment } from './client.js';

// #6 (role: "staff" | "mentor")
export const createInvite = (role) => post('/invites', { role });

// #7
export const listUsers = () => get('/users');

// #8
export const disableUser = (userId) => post(`/users/${segment(userId)}/disable`);
