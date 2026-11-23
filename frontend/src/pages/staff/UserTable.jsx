import Badge from '../../components/Badge.jsx';
import ScrollTable from '../../components/ScrollTable.jsx';
import { formatDateTime } from '../../utils/date.js';
import { roleLabel } from '../../utils/labels.js';

// Mirrors the server rule: staff disable mentors, directors disable staff
// and mentors, nobody disables themselves. The server still enforces it.
function canDisable(actor, target) {
  if (target.disabled_at || target.id === actor.id) return false;
  if (actor.role === 'director') return target.role === 'staff' || target.role === 'mentor';
  return actor.role === 'staff' && target.role === 'mentor';
}

function StatusCell({ user }) {
  if (user.disabled_at) {
    return <Badge>비활성 ({formatDateTime(user.disabled_at)})</Badge>;
  }
  if (user.assignment_ended) {
    return <Badge tone="warning">배정이 끝난 활성 계정</Badge>;
  }
  return <Badge tone="success">활성</Badge>;
}

export default function UserTable({ users, actor, onDisable }) {
  return (
    <ScrollTable label="계정 목록 표">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">이름</th>
            <th scope="col">아이디</th>
            <th scope="col">역할</th>
            <th scope="col">상태</th>
            <th scope="col">
              <span className="visually-hidden">관리</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className={user.assignment_ended && !user.disabled_at ? 'is-highlight' : undefined}>
              <th scope="row">{user.display_name}</th>
              <td className="table__mono">{user.login_id}</td>
              <td>{roleLabel(user.role)}</td>
              <td>
                <StatusCell user={user} />
              </td>
              <td>
                {canDisable(actor, user) && (
                  <div className="row">
                    <button type="button" className="btn btn--small btn--danger" onClick={() => onDisable(user)}>
                      비활성화
                    </button>
                    {user.role === 'staff' && (
                      <Badge lock>시설장 전용</Badge>
                    )}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollTable>
  );
}
