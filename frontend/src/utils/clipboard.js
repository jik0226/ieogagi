// Clipboard helpers. The browser may refuse clipboard access (permission denied,
// page not focused, insecure context), so the caller gets true/false and must tell
// the user what to do instead. The exception text is never shown or kept: it can
// describe browser internals and is of no use to the person at the screen.
export async function clearClipboard(clipboard = globalThis.navigator?.clipboard) {
  if (!clipboard?.writeText) return false;
  try {
    await clipboard.writeText('');
    return true;
  } catch {
    return false;
  }
}
