import { useCallback } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { correctRecord, listRecords } from '../../api/records.js';
import AsyncView from '../../components/AsyncView.jsx';
import NotFoundView from '../../components/NotFoundView.jsx';
import RecordFields from '../../components/RecordFields.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { formatDate } from '../../utils/date.js';
import { isNumericId } from '../../utils/ids.js';
import RecordForm from './RecordForm.jsx';

// The record is always read again with the current session, so a page
// restored from history after an account switch shows nothing of the previous
// user. `null` means it is gone (already corrected, hidden or not visible).
async function findRecord(childId, recordId) {
  const records = await listRecords(childId);
  return records.find((record) => String(record.id) === recordId) ?? null;
}

function CorrectView({ recordId, childId }) {
  const load = useCallback(() => findRecord(childId, recordId), [childId, recordId]);
  const { loading, data, error, reload } = useAsync(load);
  const submitRecord = useCallback((payload) => correctRecord(recordId, payload), [recordId]);
  const backTo = `/mentor/children/${childId}`;

  return (
    <div className="stack">
      <AsyncView loading={loading} error={error} onRetry={reload} screen>
        {data === null ? (
          <div className="alert alert--warning" role="alert">
            <p>정정할 기록을 찾을 수 없습니다. 이미 정정되었거나 볼 수 없는 기록입니다.</p>
            <Link to={backTo}>기록 목록으로 돌아가기</Link>
          </div>
        ) : (
          data && (
            <>
              <div>
                <Link className="back-link" to={backTo}>
                  ‹ 돌아가기
                </Link>
                <h1 className="page-heading">
                  기록 정정{' '}
                  <span className="page-heading__sub">{formatDate(data.session_date)}</span>
                </h1>
              </div>
              <section className="record-original" aria-labelledby="original-title">
                <h2 id="original-title">
                  원래 기록 <span className="meta">(읽기 전용)</span>
                </h2>
                <RecordFields record={data} hideEmpty />
              </section>
              <RecordForm
                mode="correct"
                initial={data}
                submitRecord={submitRecord}
                backTo={backTo}
              />
            </>
          )
        )}
      </AsyncView>
    </div>
  );
}

export default function RecordCorrectPage() {
  const { recordId } = useParams();
  const [searchParams] = useSearchParams();
  const childId = searchParams.get('childId');

  if (!isNumericId(recordId) || !isNumericId(childId)) return <NotFoundView />;
  return <CorrectView key={`${childId}:${recordId}`} recordId={recordId} childId={childId} />;
}
