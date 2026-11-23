import { useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { listMyAssignments } from '../../api/assignments.js';
import { ApiError } from '../../api/client.js';
import { createRecord } from '../../api/records.js';
import AsyncView from '../../components/AsyncView.jsx';
import NotFoundView from '../../components/NotFoundView.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { todayKst } from '../../utils/date.js';
import { isNumericId } from '../../utils/ids.js';
import { FORBIDDEN_MESSAGE } from '../../utils/messages.js';
import RecordForm from './RecordForm.jsx';

function earliest(a, b) {
  return a < b ? a : b;
}

// The period and alias are always read with the current session from the
// mentor's own assignment list (nothing is carried in history state). A child
// without an active assignment is treated like any other refusal (403).
async function loadPeriod(childId) {
  const items = await listMyAssignments();
  const found = items.find((item) => String(item.child.id) === childId && item.status === 'active');
  if (!found) {
    throw new ApiError({ status: 403, code: 'FORBIDDEN', message: FORBIDDEN_MESSAGE });
  }
  return { start_date: found.start_date, end_date: found.end_date, alias: found.child.alias };
}

function NewRecordView({ childId }) {
  const load = useCallback(() => loadPeriod(childId), [childId]);
  const { loading, data, error, reload } = useAsync(load);

  const submitRecord = useCallback((payload) => createRecord(childId, payload), [childId]);
  const backTo = `/mentor/children/${childId}`;
  const today = todayKst();
  const maxDate = data ? earliest(today, data.end_date) : today;

  return (
    <div className="stack">
      <AsyncView loading={loading} error={error} onRetry={reload} screen>
        {data && (
          <>
            <div>
              <Link className="back-link" to={backTo}>
                ‹ {data.alias ? `${data.alias} 인계 카드` : '아동 기록'}
              </Link>
              <h1 className="page-heading">수업 기록 쓰기</h1>
            </div>
            <RecordForm
              mode="create"
              initial={{ session_date: maxDate, did: '', stuck: '', next_step: '' }}
              minDate={data.start_date}
              maxDate={maxDate}
              submitRecord={submitRecord}
              backTo={backTo}
            />
          </>
        )}
      </AsyncView>
    </div>
  );
}

export default function RecordNewPage() {
  const { childId } = useParams();
  if (!isNumericId(childId)) return <NotFoundView />;
  return <NewRecordView key={childId} childId={childId} />;
}
