import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { getHandoverCard, listRecords } from '../../api/records.js';
import AsyncView from '../../components/AsyncView.jsx';
import ForbiddenView from '../../components/ForbiddenView.jsx';
import NotFoundView from '../../components/NotFoundView.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { formatPeriod } from '../../utils/date.js';
import { isNumericId } from '../../utils/ids.js';
import { isStatus } from '../../utils/messages.js';
import HandoverCardView from './HandoverCardView.jsx';
import MyRecordsList from './MyRecordsList.jsx';

// "저장했습니다" arrives through router state from the record form. It is
// remembered once and the state is cleared, so a reload does not repeat it.
function useSavedNotice() {
  const location = useLocation();
  const navigate = useNavigate();
  const [saved] = useState(() => location.state?.saved === true);

  useEffect(() => {
    if (saved) navigate(location.pathname, { replace: true, state: null });
  }, [saved, navigate, location.pathname]);

  return saved;
}

function ChildView({ childId }) {
  const loadCard = useCallback(() => getHandoverCard(childId), [childId]);
  const loadRecords = useCallback(() => listRecords(childId), [childId]);
  const card = useAsync(loadCard);
  const records = useAsync(loadRecords);
  const saved = useSavedNotice();
  const child = card.data?.child;

  // Either request refused: the whole screen becomes the blocked screen.
  if (isStatus(card.error, 403) || isStatus(records.error, 403)) return <ForbiddenView />;

  return (
    <div className="stack">
      <div className="child-hero">
        <Link className="back-link" to="/mentor">
          ‹ 내 아동
        </Link>
        <div className="child-hero__card">
          {child && (
            <span className="child-hero__tile" aria-hidden="true">
              {child.alias.slice(0, 1)}
            </span>
          )}
          <div>
            <h1 className="page-heading">
              {child ? (
                <>
                  {child.alias} <span className="page-heading__sub">{child.grade}</span>
                </>
              ) : (
                '아동 기록'
              )}
            </h1>
            {card.data && (
              <p className="child-hero__period">
                {formatPeriod(card.data.assignment.start_date, card.data.assignment.end_date)}
              </p>
            )}
          </div>
        </div>
      </div>

      {saved && (
        <div className="alert alert--success" role="status">
          저장했습니다
        </div>
      )}

      {card.data && (
        <Link className="btn btn--primary btn--block" to={`/mentor/children/${childId}/records/new`}>
          ＋ 오늘 기록 쓰기
        </Link>
      )}

      <AsyncView loading={card.loading} error={card.error} onRetry={card.reload}>
        {card.data && <HandoverCardView card={card.data} />}
      </AsyncView>

      <section className="stack" aria-labelledby="my-records-title">
        <h2 id="my-records-title" className="section-title">
          내가 쓴 기록
        </h2>
        <AsyncView loading={records.loading} error={records.error} onRetry={records.reload} cards={1}>
          {records.data && <MyRecordsList childId={childId} records={records.data} />}
        </AsyncView>
      </section>
    </div>
  );
}

export default function ChildPage() {
  const { childId } = useParams();
  if (!isNumericId(childId)) return <NotFoundView />;
  return <ChildView key={childId} childId={childId} />;
}
