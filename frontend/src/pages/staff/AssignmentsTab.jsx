import { useCallback } from 'react';
import { listUsers } from '../../api/accounts.js';
import { listChildren } from '../../api/children.js';
import AsyncView from '../../components/AsyncView.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import AssignmentManager from './AssignmentManager.jsx';

// Loads the mentor and child lists once, then hands them to the manager.
export default function AssignmentsTab({ onChanged }) {
  const loadUsers = useCallback(() => listUsers(), []);
  const loadChildren = useCallback(() => listChildren(), []);
  const users = useAsync(loadUsers);
  const children = useAsync(loadChildren);

  function retry() {
    users.reload();
    children.reload();
  }

  const mentors = users.data ? users.data.filter((user) => user.role === 'mentor' && !user.disabled_at) : [];

  return (
    <AsyncView
      loading={users.loading || children.loading}
      error={users.error || children.error}
      onRetry={retry}
    >
      {users.data && children.data && <AssignmentManager mentors={mentors} childList={children.data} onChanged={onChanged} />}
    </AsyncView>
  );
}
