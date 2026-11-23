import { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import { getMe, login as apiLogin, logout as apiLogout } from '../api/auth.js';
import { setUnauthorizedHandler } from '../api/client.js';

export const AuthContext = createContext(null);

const LOADING = { status: 'loading', user: null, error: null, expired: false };
const ANONYMOUS = { status: 'anonymous', user: null, error: null, expired: false };
// A signed-in session that the server no longer accepts (idle timeout,
// log-out elsewhere, disabled account): the login page shows a banner.
const EXPIRED = { status: 'anonymous', user: null, error: null, expired: true };

// Holds the signed-in user. The session itself is an HttpOnly cookie that
// the browser sends on its own, so nothing is persisted here.
export function AuthProvider({ children }) {
  const [state, setState] = useState(LOADING);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    getMe().then(
      (user) => {
        if (active) setState({ status: 'authenticated', user, error: null, expired: false });
      },
      (error) => {
        if (!active) return;
        setState(error.status === 401 ? ANONYMOUS : { status: 'error', user: null, error, expired: false });
      },
    );
    return () => {
      active = false;
    };
  }, [attempt]);

  // Any later 401 means the session ended while the user was working.
  useEffect(
    () =>
      setUnauthorizedHandler(() =>
        setState((current) => (current.status === 'authenticated' ? EXPIRED : current)),
      ),
    [],
  );

  const retry = useCallback(() => {
    setState(LOADING);
    setAttempt((current) => current + 1);
  }, []);

  const login = useCallback(async (credentials) => {
    const user = await apiLogin(credentials);
    setState({ status: 'authenticated', user, error: null, expired: false });
    return user;
  }, []);

  // The screen forgets the account even when the logout request fails (network,
  // expired session): nothing of the previous account may stay rendered or in memory.
  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setState(ANONYMOUS);
    }
  }, []);

  const value = useMemo(() => ({ ...state, login, logout, retry }), [state, login, logout, retry]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
