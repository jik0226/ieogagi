import { useCallback, useMemo, useState } from 'react';
import { listUsers } from '../../api/accounts.js';
import { listAuditLogs } from '../../api/audit.js';
import AsyncView from '../../components/AsyncView.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import AuditFilters from './AuditFilters.jsx';
import AuditTable from './AuditTable.jsx';

const PAGE_SIZE = 50;
const NO_FILTERS = { action: '', result: '', dateFrom: '', dateTo: '' };

export default function AuditTab() {
  const [filters, setFilters] = useState(NO_FILTERS);
  const [offset, setOffset] = useState(0);
  const load = useCallback(
    () => listAuditLogs({ ...filters, limit: PAGE_SIZE, offset }),
    [filters, offset],
  );
  const { loading, data, error, reload } = useAsync(load);

  // Actor names come from the account list. If it cannot be read, the table shows
  // the numeric ID and a notice says so, instead of the error being swallowed
  // (security diagnosis 04.02).
  const users = useAsync(listUsers);
  const actorNames = useMemo(
    () => new Map((users.data ?? []).map((user) => [user.id, user.display_name])),
    [users.data],
  );

  function applyFilters(next) {
    setFilters(next);
    setOffset(0);
  }

  const total = data?.total ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);
  // Counted over the rows on this page only, so the chip names the page size.
  const flagged = (data?.items ?? []).filter((log) => log.result !== 'success').length;

  return (
    <div className="stack">
      <AuditFilters initial={filters} onApply={applyFilters} />
      <AsyncView loading={loading} error={error} onRetry={reload}>
        {data && data.items.length === 0 && <EmptyState>조건에 맞는 감사 로그가 없습니다.</EmptyState>}
        {data && data.items.length > 0 && (
          <>
            <div className="audit-summary">
              <p className="audit-summary__total">
                전체 <strong>{total}</strong>건
              </p>
              {flagged > 0 && (
                <span className="audit-summary__chip audit-summary__chip--danger">
                  이 쪽 {data.items.length}건 중 거부·실패 {flagged}건
                </span>
              )}
            </div>
            {users.error && (
              <div className="alert alert--warning" role="status">
                <p>계정 목록을 불러오지 못해 작업자를 이름 대신 번호로 보여 줍니다.</p>
                <button type="button" className="btn btn--small" onClick={users.reload}>
                  이름 다시 불러오기
                </button>
              </div>
            )}
            <AuditTable items={data.items} actorNames={actorNames} />
            <div className="audit-pager">
              <button
                type="button"
                className="btn btn--small"
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
              >
                ‹ 이전
              </button>
              <span className="audit-pager__where" role="status">
                {from}–{to} / {total}
              </span>
              <button
                type="button"
                className="btn btn--small"
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
              >
                다음 ›
              </button>
            </div>
          </>
        )}
      </AsyncView>
    </div>
  );
}
