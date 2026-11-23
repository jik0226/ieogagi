import { get, post, segment } from './client.js';

// #17
export const getHandoverCard = (childId) =>
  get(`/children/${segment(childId)}/handover-card`);

// #18 (mentors get MentorRecord[], director/staff get StaffRecord[])
export const listRecords = (childId) => get(`/children/${segment(childId)}/records`);

// #19
export const createRecord = (childId, { session_date, did, stuck, next_step, sensitive_confirmed }) =>
  post(`/children/${segment(childId)}/records`, {
    session_date,
    did,
    stuck,
    next_step,
    sensitive_confirmed,
  });

// #20
export const correctRecord = (recordId, { did, stuck, next_step, sensitive_confirmed }) =>
  post(`/records/${segment(recordId)}/corrections`, {
    did,
    stuck,
    next_step,
    sensitive_confirmed,
  });

// #21
export const hideRecord = (recordId, reasonCode) =>
  post(`/records/${segment(recordId)}/hide`, { reason_code: reasonCode });

// #22 (fields: any of "did" | "stuck" | "next_step")
export const redactRecord = (recordId, fields) =>
  post(`/records/${segment(recordId)}/redact`, { fields });
