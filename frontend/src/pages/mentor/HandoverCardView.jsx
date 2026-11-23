import EmptyState from '../../components/EmptyState.jsx';
import RecordFields from '../../components/RecordFields.jsx';
import { formatDate } from '../../utils/date.js';

// Hand-over card: the staff's share texts first, then the last records from
// before this assignment began, newest on top, as a timeline. The "next
// step" is the strongest line of each session.
export default function HandoverCardView({ card }) {
  const count = card.records.length;

  return (
    <section className="stack" aria-labelledby="handover-title">
      {card.share_texts.length > 0 && (
        <div className="share-box">
          <h3>담당 선생님 공유 문구</h3>
          <ul>
            {card.share_texts.map((text, index) => (
              <li key={`${index}-${text}`} className="pre-wrap">
                {text}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="handover-title">
        <h2 id="handover-title">인계 카드</h2>
        <p className="meta">{count > 0 ? `배정 시작 전 최근 ${count}회 · 최근 것이 위` : '배정 시작 전 기록'}</p>
      </div>

      {count === 0 ? (
        <EmptyState>첫 배정이라 이전 기록이 없습니다</EmptyState>
      ) : (
        <ul className="handover-timeline">
          {card.records.map((record) => (
            <li key={record.session_no} className="handover-timeline__item">
              <p className="handover-timeline__head">
                {record.session_no}회차 · {formatDate(record.session_date)} · 이전 선생님
              </p>
              <RecordFields record={record} emphasize="next_step" hideEmpty past />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
