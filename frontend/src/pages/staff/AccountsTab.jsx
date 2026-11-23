import { useCallback, useState } from 'react';
import { disableUser, listUsers } from '../../api/accounts.js';
import AsyncView from '../../components/AsyncView.jsx';
import ConfirmDialog from '../../components/ConfirmDialog.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { useAuth } from '../../auth/useAuth.js';
import { useAsync } from '../../hooks/useAsync.js';
import { useMutation } from '../../hooks/useMutation.js';
import InviteForm from './InviteForm.jsx';
import UserTable from './UserTable.jsx';

export default function AccountsTab({ onChanged }) {
  const { user } = useAuth();
  const load = useCallback(() => listUsers(), []);
  const { loading, data, error, reload } = useAsync(load);
  const [target, setTarget] = useState(null);
  const disable = useMutation(disableUser);

  async function handleDisable() {
    const result = await disable.run(target.id);
    if (result.ok) {
      setTarget(null);
      reload();
      onChanged();
    }
  }

  function closeDialog() {
    disable.reset();
    setTarget(null);
  }

  return (
    <div className="split split--aside">
      <InviteForm actorRole={user.role} />
      <section className="stack" aria-labelledby="users-title">
        <h2 id="users-title">계정 목록</h2>
        <AsyncView loading={loading} error={error} onRetry={reload}>
          {data && data.length === 0 && <EmptyState>계정이 없습니다.</EmptyState>}
          {data && data.length > 0 && <UserTable users={data} actor={user} onDisable={setTarget} />}
        </AsyncView>
      </section>

      {target && (
        <ConfirmDialog
          title="계정 비활성화"
          confirmLabel="비활성화"
          danger
          busy={disable.busy}
          error={disable.error}
          onConfirm={handleDisable}
          onCancel={closeDialog}
        >
          <p>
            <strong>{target.display_name}</strong>({target.login_id}) 계정을 비활성화합니다. 이 사람의 로그인
            세션이 모두 끊기고 다시 로그인할 수 없습니다.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}
