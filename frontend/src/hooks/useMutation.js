import { useCallback, useState } from 'react';

// Wraps a write call. `run(...args)` resolves to { ok, data } or { ok, error }
// and never throws, so event handlers stay simple. A response the client could
// not read is an ApiError (code INVALID_RESPONSE), so it lands in { ok: false }
// and forms keep what the user typed. Errors accepted by `skipError` are
// returned to the caller but not stored for display.
export function useMutation(action, { skipError } = {}) {
  const [state, setState] = useState({ busy: false, error: null });

  const run = useCallback(
    async (...args) => {
      setState({ busy: true, error: null });
      try {
        const data = await action(...args);
        setState({ busy: false, error: null });
        return { ok: true, data };
      } catch (error) {
        const hidden = skipError ? skipError(error) : false;
        setState({ busy: false, error: hidden ? null : error });
        return { ok: false, error };
      }
    },
    [action, skipError],
  );

  const reset = useCallback(() => setState({ busy: false, error: null }), []);

  return { run, reset, busy: state.busy, error: state.error };
}
