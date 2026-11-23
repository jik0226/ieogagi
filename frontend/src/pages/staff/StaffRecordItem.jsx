import Badge from '../../components/Badge.jsx';
import RecordFields from '../../components/RecordFields.jsx';
import { formatDate, formatDateTime } from '../../utils/date.js';
import { hideReasonLabel } from '../../utils/labels.js';

// One record in the staff view. Four badges explain its state:
// 정정본 / 정정되어 대체됨 / 숨김 · 사유 / 일부 칸 지움.
// Replaced and hidden records are drawn grey, with text kept readable.
export default function StaffRecordItem({ record, onHide, onRedact }) {
  const hidden = Boolean(record.hidden_at);
  const dimmed = hidden || record.superseded;

  return (
    <article className={dimmed ? 'card record record--muted staff-record' : 'card record staff-record'}>
      <header className="staff-record__head">
        {record.session_no != null && (
          <span className="staff-record__no">
            {record.session_no}
            <span className="staff-record__no-unit">회</span>
          </span>
        )}
        <div className="staff-record__when">
          <strong className="staff-record__date">{formatDate(record.session_date)}</strong>
          <span className="staff-record__author">{record.author.display_name} 작성</span>
        </div>
        <div className="staff-record__badges">
          {record.corrects_id !== null && <Badge>정정본</Badge>}
          {record.superseded && <Badge>정정되어 대체됨</Badge>}
          {hidden && <Badge tone="danger">숨김 · {hideReasonLabel(record.hidden_reason_code)}</Badge>}
          {record.redacted_at && <Badge tone="warning">일부 칸 지움</Badge>}
        </div>
      </header>
      {hidden && <p className="meta">{formatDateTime(record.hidden_at)}에 숨김</p>}
      <RecordFields record={record} />
      <div className="staff-record__actions">
        {!hidden && (
          <button type="button" className="btn btn--small" onClick={onHide}>
            숨기기
          </button>
        )}
        <button type="button" className="btn btn--small" onClick={onRedact}>
          민감정보 칸 지우기
        </button>
      </div>
    </article>
  );
}
