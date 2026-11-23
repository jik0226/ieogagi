import { del, get, post, segment } from './client.js';

// #9
export const createChild = ({ alias, grade, privacy_consent_confirmed, sensitive_basis_confirmed }) =>
  post('/children', { alias, grade, privacy_consent_confirmed, sensitive_basis_confirmed });

// #10
export const listChildren = () => get('/children');

// #11
export const confirmSensitiveBasis = (childId) =>
  post(`/children/${segment(childId)}/sensitive-basis`);

// #12
export const destroyChild = (childId) => del(`/children/${segment(childId)}`);
