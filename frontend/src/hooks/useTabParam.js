import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

// The open tab lives in the address (?tab=…), so a reload or a shared link
// opens the same tab. Unknown values fall back to the first tab.
export function useTabParam(tabIds) {
  const [params, setParams] = useSearchParams();
  const requested = params.get('tab');
  const active = tabIds.includes(requested) ? requested : tabIds[0];

  const setActive = useCallback(
    (id) => setParams({ tab: id }, { replace: true }),
    [setParams],
  );

  return [active, setActive];
}
