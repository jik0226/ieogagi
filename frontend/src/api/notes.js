import { get, post, segment } from './client.js';

// #23 (body and share_text are both optional, at least one is required)
export const createNote = (childId, { body, share_text }) =>
  post(`/children/${segment(childId)}/notes`, { body, share_text });

// #24
export const listNotes = (childId) => get(`/children/${segment(childId)}/notes`);

// #25
export const getNote = (noteId) => get(`/notes/${segment(noteId)}`);
