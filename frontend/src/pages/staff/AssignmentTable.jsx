import Badge from '../../components/Badge.jsx';
import ScrollTable from '../../components/ScrollTable.jsx';
import { formatPeriod } from '../../utils/date.js';
import { assignmentStatus } from '../../utils/labels.js';

// Only running or not-yet-started assignments can be revoked.
function canRevoke(item) {
  return item.status === 'active' || item.status === 'upcoming';
}

export default function AssignmentTable({ items, onRevoke }) {
  const sorted = [...items].sort((a, b) => b.start_date.localeCompare(a.start_date));

  return (
    <ScrollTable label="배정 목록 표">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">멘토</th>
            <th scope="col">아동</th>
            <th scope="col">기간</th>
            <th scope="col">상태</th>
            <th scope="col">
              <span className="visually-hidden">관리</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => {
            const status = assignmentStatus(item.status);
            return (
              <tr key={item.id}>
                <td>{item.mentor_name}</td>
                <td>{item.child_alias}</td>
                <td>{formatPeriod(item.start_date, item.end_date)}</td>
                <td>
                  <Badge tone={status.tone}>{status.label}</Badge>
                </td>
                <td>
                  {canRevoke(item) && (
                    <button type="button" className="btn btn--small btn--danger" onClick={() => onRevoke(item)}>
                      회수
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </ScrollTable>
  );
}
