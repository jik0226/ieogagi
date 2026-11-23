import { useState } from 'react';
import { createInvite } from '../../api/accounts.js';
import CopyButton from '../../components/CopyButton.jsx';
import ErrorMessage from '../../components/ErrorMessage.jsx';
import { SelectField } from '../../components/FormFields.jsx';
import { useMutation } from '../../hooks/useMutation.js';
import { formatDateTime } from '../../utils/date.js';
import { clearClipboard } from '../../utils/clipboard.js';
import { roleLabel } from '../../utils/labels.js';

// Directors may invite staff and mentors; staff may invite mentors only.
function roleOptionsFor(actorRole) {
  const options = [{ value: 'mentor', label: roleLabel('mentor') }];
  if (actorRole === 'director') options.push({ value: 'staff', label: roleLabel('staff') });
  return options;
}

export default function InviteForm({ actorRole }) {
  const [role, setRole] = useState('mentor');
  const [issued, setIssued] = useState(null);
  const [copied, setCopied] = useState(false);
  const [clipboardLeft, setClipboardLeft] = useState(false);
  const { run, busy, error } = useMutation(createInvite);

  // Hiding the code also clears the clipboard if we put the one-time code there, so it
  // is not left for the next person on a shared center PC. The browser may refuse; then
  // the user is told to overwrite it (fixed wording, no error details) instead of the
  // failure being ignored (security diagnosis 04.02, empty catch block).
  async function hideCode() {
    setIssued(null);
    setClipboardLeft(false);
    if (!copied) return;
    setCopied(false);
    if (!(await clearClipboard())) setClipboardLeft(true);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setIssued(null);
    setCopied(false);
    setClipboardLeft(false);
    const result = await run(role);
    if (result.ok) setIssued(result.data);
  }

  return (
    <form className="form card" onSubmit={handleSubmit} aria-labelledby="invite-title">
      <h2 id="invite-title">초대 코드 발급</h2>
      <SelectField
        label="초대할 역할"
        value={role}
        onChange={setRole}
        options={roleOptionsFor(actorRole)}
        hint={actorRole === 'director' ? undefined : '담당자 초대는 시설장만 할 수 있습니다.'}
      />
      {error && <ErrorMessage error={error} />}
      <div className="form-actions">
        <button type="submit" className="btn btn--primary" disabled={busy}>
          {busy ? '발급 중…' : '코드 발급'}
        </button>
      </div>
      {issued && (
        <div className="alert alert--warning" role="status">
          <p className="meta">{roleLabel(issued.role)} 초대 코드</p>
          <p className="code-box">{issued.code}</p>
          <div className="row">
            <CopyButton text={issued.code} label="복사" onCopied={() => setCopied(true)} />
            <button type="button" className="btn btn--small" onClick={hideCode}>
              코드 숨기기
            </button>
          </div>
          <p>
            <strong>이 코드는 지금 한 번만 보입니다 · 72시간 동안 1회 사용</strong>
          </p>
          <p className="meta">만료 {formatDateTime(issued.expires_at)}</p>
          <p className="meta">코드를 숨기면 복사해 둔 코드도 클립보드에서 지웁니다.</p>
        </div>
      )}
      {clipboardLeft && (
        <div className="alert alert--warning" role="alert">
          <p>
            <strong>클립보드에서 초대 코드를 지우지 못했습니다.</strong>
          </p>
          <p>브라우저가 클립보드 지우기를 허용하지 않았습니다. 다른 글자를 한 번 복사해 초대 코드를 덮어 써 주세요.</p>
        </div>
      )}
    </form>
  );
}
