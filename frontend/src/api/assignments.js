import { get, post, segment } from './client.js';

// #13
export const createAssignment = ({ mentor_id, child_id, start_date, end_date }) =>
  post('/assignments', { mentor_id, child_id, start_date, end_date });

// #14 (both filters are optional)
export const listAssignments = ({ childId, mentorId } = {}) =>
  get('/assignments', { query: { child_id: childId, mentor_id: mentorId } });

// #15
export const revokeAssignment = (assignmentId) =>
  post(`/assignments/${segment(assignmentId)}/revoke`);

// #16
export const listMyAssignments = () => get('/me/assignments');
