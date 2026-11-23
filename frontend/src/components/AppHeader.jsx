import { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/useAuth.js';
import { homePathFor, isStaffRole } from '../auth/roles.js';
import { describeError } from '../utils/messages.js';
import { roleLabel } from '../utils/labels.js';

export default function AppHeader({ variant }) {
  const { user, logout } = useAuth();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleLogout() {
    setBusy(true);
    setError(null);
    try {
      await logout();
    } catch (caught) {
      setError(describeError(caught));
      setBusy(false);
    }
  }

  return (
    <header className={`app-header app-header--${variant}`}>
      <Link className="app-header__brand" to={homePathFor(user.role)}>
        이어가기
      </Link>
      {isStaffRole(user.role) && (
        <nav className="app-header__nav" aria-label="주요 메뉴">
          <NavLink to="/staff" end>
            <svg className="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
              <rect x="3" y="3" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="2" />
              <rect x="14" y="3" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="2" />
              <rect x="3" y="14" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="2" />
              <rect x="14" y="14" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="2" />
            </svg>
            아동·배정·계정
          </NavLink>
          <NavLink to="/staff/records">
            <svg className="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
              <path d="M6 3h9l4 4v14H6z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
              <path d="M9 12h7M9 16h7M9 8h3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            기록·메모·감사 로그
          </NavLink>
        </nav>
      )}
      <span className="app-header__who">
        {user.center.name} · {user.display_name} ({roleLabel(user.role)})
      </span>
      <button
        type="button"
        className="btn btn--small app-header__logout"
        onClick={handleLogout}
        disabled={busy}
      >
        로그아웃
      </button>
      {error && (
        <span className="field__error app-header__error" role="alert">
          {error}
        </span>
      )}
    </header>
  );
}
