import { useCallback, useState } from 'react';
import { listAssignments, revokeAssignment } from '../../api/assignments.js';
import AsyncView from '../../components/AsyncView.jsx';
import ConfirmDialog from '../../components/ConfirmDialog.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { SelectField } from '../../components/FormFields.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useMutation } from '../../hooks/useMutation.js';
import { formatPeriod } from '../../utils/date.js';
import AssignmentForm from './AssignmentForm.jsx';
import AssignmentTable from './AssignmentTable.jsx';

export default function AssignmentManager({ mentors, childList, onChanged }) {
  const [childFilter, setChildFilter] = useState('');
  const [mentorFilter, setMentorFilter] = useState('');
  const [revokeTarget, setRevokeTarget] = useState(null);
  const load = useCallback(
    () => listAssignments({ childId: childFilter, mentorId: mentorFilter }),
    [childFilter, mentorFilter],
  );
  const { loading, data, error, reload } = useAsync(load);
  const revoke = useMutation(revokeAssignment);

  const childOptions = childList.map((child) => ({ value: String(child.id), label: `${child.alias} (${child.grade})` }));
  const mentorOptions = mentors.map((mentor) => ({ value: String(mentor.id), label: mentor.display_name }));

  async function handleRevoke() {
    const result = await revoke.run(revokeTarget.id);
    if (result.ok) {
      setRevokeTarget(null);
      reload();
      onChanged();
    }
  }

  function handleCreated() {
    reload();
    onChanged();
  }

  function closeRevoke() {
    revoke.reset();
    setRevokeTarget(null);
  }

  return (
    <div className="split split--aside">
      <AssignmentForm
        mentorOptions={mentorOptions}
        childOptions={childOptions}
        onCreated={handleCreated}
      />

      <section className="stack" aria-labelledby="assignments-title">
        <h2 id="assignments-title">배정 목록</h2>
        <div className="grid-2">
          <SelectField
            label="아동으로 거르기"
            value={childFilter}
            onChange={setChildFilter}
            options={childOptions}
            placeholder="전체 아동"
          />
          <SelectField
            label="멘토로 거르기"
            value={mentorFilter}
            onChange={setMentorFilter}
            options={mentorOptions}
            placeholder="전체 멘토"
          />
        </div>
        <AsyncView loading={loading} error={error} onRetry={reload}>
          {data && data.length === 0 && <EmptyState>조건에 맞는 배정이 없습니다.</EmptyState>}
          {data && data.length > 0 && <AssignmentTable items={data} onRevoke={setRevokeTarget} />}
        </AsyncView>
      </section>

      {revokeTarget && (
        <ConfirmDialog
          title="배정 회수"
          confirmLabel="회수"
          danger
          busy={revoke.busy}
          error={revoke.error}
          onConfirm={handleRevoke}
          onCancel={closeRevoke}
        >
          <p>
            회수하면 <strong>{revokeTarget.mentor_name}</strong> 멘토는{' '}
            <strong>다음 요청부터</strong> <strong>{revokeTarget.child_alias}</strong>의 기록을 볼 수
            없습니다.
          </p>
          <p className="meta">배정 기간 {formatPeriod(revokeTarget.start_date, revokeTarget.end_date)}</p>
        </ConfirmDialog>
      )}
    </div>
  );
}
