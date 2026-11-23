import { useEffect, useState } from 'react';
import { listUsers } from '../api/accounts.js';
import { listChildren } from '../api/children.js';

// "확인이 필요한 항목": the counts staff act on, each a button that opens the
// tab where the work is done. Counts come from the same lists the tabs
// already read, so no new API is needed.
async function loadCounts() {
  const [children, users] = await Promise.all([listChildren(), listUsers()]);
  return {
    sensitive: children.filter((child) => !child.sensitive_basis_at).length,
    ended: users.filter((user) => user.assignment_ended && !user.disabled_at).length,
  };
}

function Icon({ name }) {
  const common = { stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' };
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
      {name === 'shield' && (
        <>
          <path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6z" {...common} />
          <path d="m9 12 2 2 4-4" {...common} />
        </>
      )}
      {name === 'user' && (
        <>
          <circle cx="12" cy="8" r="4" {...common} />
          <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" {...common} />
        </>
      )}
    </svg>
  );
}

const TILES = [
  { key: 'sensitive', tab: 'children', icon: 'shield', tone: 'peach', label: '민감정보 미확인 아동', unit: '명', hint: '아동 탭에서 확인' },
  { key: 'ended', tab: 'accounts', icon: 'user', tone: 'butter', label: '배정 끝난 활성 계정', unit: '개', hint: '계정 탭에서 정리' },
];

// `refreshKey` changes whenever the counts may be out of date (the user
// handled an item in a tab, or switched tabs): the counts are read again and
// the old numbers stay on screen until the new ones arrive.
export default function StaffTodo({ refreshKey, onOpen }) {
  const [state, setState] = useState({ key: null, data: null, failed: false });
  const loading = state.key !== refreshKey;

  useEffect(() => {
    let active = true;
    loadCounts().then(
      (data) => {
        if (active) setState({ key: refreshKey, data, failed: false });
      },
      () => {
        if (active) setState((current) => ({ ...current, key: refreshKey, failed: true }));
      },
    );
    return () => {
      active = false;
    };
  }, [refreshKey]);

  // A failed count must never block the page; the tabs below still work.
  if (state.failed) return null;

  return (
    <section className="staff-todo" aria-labelledby="staff-todo-title">
      <h2 id="staff-todo-title" className="staff-todo__title">
        확인이 필요한 항목
      </h2>
      <ul className="staff-todo__list">
        {TILES.map((tile) => {
          const count = state.data ? state.data[tile.key] : null;
          return (
            <li key={tile.key}>
              <button
                type="button"
                className={`staff-todo__tile staff-todo__tile--${tile.tone}`}
                onClick={() => onOpen(tile.tab)}
                aria-busy={loading ? true : undefined}
              >
                <span className="staff-todo__icon">
                  <Icon name={tile.icon} />
                </span>
                <span className="staff-todo__body">
                  <span className="staff-todo__label">{tile.label}</span>
                  <span className="staff-todo__count">
                    {count === null ? '–' : count}
                    <small>{tile.unit}</small>
                  </span>
                  <span className="staff-todo__hint">{tile.hint} ›</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
