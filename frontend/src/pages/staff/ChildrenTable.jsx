import Badge from '../../components/Badge.jsx';
import ScrollTable from '../../components/ScrollTable.jsx';
import { formatDateOnly } from '../../utils/date.js';

// Registered children. "파기" is drawn only for the director; the server
// refuses it for anyone else as well.
export default function ChildrenTable({ items, isDirector, onConfirmBasis, onDestroy }) {
  return (
    <ScrollTable label="등록된 아동 표">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">별칭</th>
            <th scope="col">학년</th>
            <th scope="col">개인정보 동의</th>
            <th scope="col">민감정보</th>
            <th scope="col">관리</th>
          </tr>
        </thead>
        <tbody>
          {items.map((child) => (
            <tr key={child.id}>
              <th scope="row">{child.alias}</th>
              <td>{child.grade}</td>
              <td>{formatDateOnly(child.consent_at)}</td>
              <td>
                {child.sensitive_basis_at ? (
                  <Badge tone="success">확인 {formatDateOnly(child.sensitive_basis_at)}</Badge>
                ) : (
                  <Badge tone="warning">미확인</Badge>
                )}
              </td>
              <td>
                <div className="row">
                  {!child.sensitive_basis_at && (
                    <button type="button" className="btn btn--small" onClick={() => onConfirmBasis(child)}>
                      민감정보 확인
                    </button>
                  )}
                  {isDirector && (
                    <>
                      <button
                        type="button"
                        className="btn btn--small btn--danger"
                        onClick={() => onDestroy(child)}
                      >
                        파기
                      </button>
                      <Badge tone="neutral" lock>
                        시설장 전용
                      </Badge>
                    </>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollTable>
  );
}
