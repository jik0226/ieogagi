import { Link } from 'react-router-dom';
import Badge from '../../components/Badge.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import RecordFields from '../../components/RecordFields.jsx';
import { formatDate } from '../../utils/date.js';

function sortNewestFirst(records) {
  return [...records].sort((a, b) => {
    const byDate = b.session_date.localeCompare(a.session_date);
    return byDate !== 0 ? byDate : b.id - a.id;
  });
}

// Records the mentor wrote during this assignment. A corrected record shows
// only its latest version, marked "정정됨".
export default function MyRecordsList({ childId, records }) {
  const sorted = sortNewestFirst(records);

  if (sorted.length === 0) {
    return <EmptyState>아직 쓴 기록이 없습니다</EmptyState>;
  }

  return (
    <ul className="card-list">
      {sorted.map((record) => (
        <li key={record.id} className="card record">
          <div className="record__head">
            <strong>{formatDate(record.session_date)}</strong>
            {record.corrects_id !== null && <Badge>정정됨</Badge>}
          </div>
          <RecordFields record={record} hideEmpty />
          <div className="record__actions">
            {/* Only ids travel in the URL: the correction page reads the record
                again with the current session (no record body in history state). */}
            <Link className="btn" to={`/mentor/records/${record.id}/correct?childId=${childId}`}>
              정정하기
            </Link>
          </div>
        </li>
      ))}
    </ul>
  );
}
