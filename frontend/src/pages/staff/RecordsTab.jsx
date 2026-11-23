import { useCallback, useId, useState } from 'react';
import { listChildren } from '../../api/children.js';
import AsyncView from '../../components/AsyncView.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import NotesPanel from './NotesPanel.jsx';
import StaffRecordList from './StaffRecordList.jsx';

// Pick a child, then read all records (left) and write notes (right).
export default function RecordsTab() {
  const load = useCallback(() => listChildren(), []);
  const { loading, data, error, reload } = useAsync(load);
  const [childId, setChildId] = useState('');

  const radioName = useId();
  const selected = data?.find((child) => String(child.id) === childId);

  return (
    <div className="stack">
      <AsyncView loading={loading} error={error} onRetry={reload}>
        {data && data.length === 0 && <EmptyState>등록된 아동이 없습니다. 아동을 먼저 등록해 주세요.</EmptyState>}
        {data && data.length > 0 && (
          <fieldset className="child-picker">
            <legend className="child-picker__legend">아동 선택</legend>
            {data.map((child) => (
              <label key={child.id} className="chip">
                <input
                  type="radio"
                  className="chip__input"
                  name={radioName}
                  value={String(child.id)}
                  checked={childId === String(child.id)}
                  onChange={() => setChildId(String(child.id))}
                />
                <span className="chip__text">
                  {child.alias}
                  <span className="chip__sub">{child.grade}</span>
                </span>
              </label>
            ))}
          </fieldset>
        )}
      </AsyncView>
      {data && data.length > 0 && !selected && <EmptyState>기록을 볼 아동을 고르세요</EmptyState>}
      {selected && (
        <div className="split split--records">
          <StaffRecordList key={`records-${selected.id}`} childId={String(selected.id)} />
          <NotesPanel key={`notes-${selected.id}`} child={selected} />
        </div>
      )}
    </div>
  );
}
