// Diagnosis 04.02 regression (empty catch in InviteForm): a failed clipboard clear
// must come back as `false` so the form can warn the user, never vanish silently.
// Run with `npm --prefix frontend test` (Node's built-in test runner, no extra packages).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { clearClipboard } from '../src/utils/clipboard.js';

test('reports success after overwriting the clipboard with an empty string', async () => {
  const written = [];
  const clipboard = { writeText: async (text) => written.push(text) };
  assert.equal(await clearClipboard(clipboard), true);
  assert.deepEqual(written, ['']);
});

test('reports failure when the browser refuses clipboard access', async () => {
  const clipboard = {
    writeText: async () => {
      throw new DOMException('Write permission denied.', 'NotAllowedError');
    },
  };
  assert.equal(await clearClipboard(clipboard), false);
});

test('reports failure when the clipboard API is missing', async () => {
  assert.equal(await clearClipboard(undefined), false);
  assert.equal(await clearClipboard({}), false);
});
