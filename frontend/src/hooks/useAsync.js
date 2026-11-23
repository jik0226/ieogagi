import { useCallback, useEffect, useState } from 'react';

const INITIAL = { load: null, version: -1, data: null, error: null };

// Runs `load` (a stable function, wrap it in useCallback) and reports
// loading / data / error. A new `load` or `reload()` starts a fresh request.
export function useAsync(load) {
  const [version, setVersion] = useState(0);
  const [result, setResult] = useState(INITIAL);

  useEffect(() => {
    let active = true;
    load().then(
      (data) => {
        if (active) setResult({ load, version, data, error: null });
      },
      (error) => {
        if (active) setResult({ load, version, data: null, error });
      },
    );
    return () => {
      active = false;
    };
  }, [load, version]);

  const reload = useCallback(() => setVersion((current) => current + 1), []);
  const loading = result.load !== load || result.version !== version;

  return {
    loading,
    data: loading ? null : result.data,
    error: loading ? null : result.error,
    reload,
  };
}
