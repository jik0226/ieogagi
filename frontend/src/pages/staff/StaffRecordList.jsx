import { useCallback, useState } from 'react';
import { listRecords } from '../../api/records.js';
import AsyncView from '../../components/AsyncView.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import HideDialog from './HideDialog.jsx';
import RedactDialog from './RedactDialog.jsx';
import StaffRecordItem from './StaffRecordItem.jsx';

function sortNewestFirst(records) {
  return [...records].sort((a, b) => {
    const byDate = b.session_date.localeCompare(a.session_date);
    return byDate !== 0 ? byDate : b.id - a.id;
  });
}

export default function StaffRecordList({ childId }) {
  const load = useCallback(() => listRecords(childId), [childId]);
  const { loading, data, error, reload } = useAsync(load);
  const [action, setAction] = useState(null);

  function handleDone() {
    setAction(null);
    reload();
  }

  return (
    <section className="stack" aria-labelledby="staff-records-title">
      <header className="panel-head">
        <h2 id="staff-records-title">회차 기록</h2>
        <p className="panel-head__sub">{data ? `전체 ${data.length}개 · 최근 것이 위` : '전체'}</p>
      </header>
      <AsyncView loading={loading} error={error} onRetry={reload}>
        {data && data.length === 0 && <EmptyState>이 아동의 기록이 아직 없습니다.</EmptyState>}
        {data && data.length > 0 && (
          <ul className="card-list">
            {sortNewestFirst(data).map((record) => (
              <li key={record.id}>
                <StaffRecordItem
                  record={record}
                  onHide={() => setAction({ type: 'hide', record })}
                  onRedact={() => setAction({ type: 'redact', record })}
                />
              </li>
            ))}
          </ul>
        )}
      </AsyncView>

      {action?.type === 'hide' && (
        <HideDialog record={action.record} onClose={() => setAction(null)} onDone={handleDone} />
      )}
      {action?.type === 'redact' && (
        <RedactDialog record={action.record} onClose={() => setAction(null)} onDone={handleDone} />
      )}
    </section>
  );
}
