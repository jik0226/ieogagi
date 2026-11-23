import { useCallback } from 'react';
import { listNotes } from '../../api/notes.js';
import AsyncView from '../../components/AsyncView.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import NoteForm from './NoteForm.jsx';
import NoteItem from './NoteItem.jsx';

export default function NotesPanel({ child }) {
  const childId = String(child.id);
  const load = useCallback(() => listNotes(childId), [childId]);
  const { loading, data, error, reload } = useAsync(load);

  return (
    <section className="stack notes" aria-labelledby="notes-title">
      <header className="panel-head">
        <h2 id="notes-title">담당자 메모</h2>
        <p className="panel-head__sub">{data ? `${data.length}개 기록됨` : '메모'}</p>
      </header>
      <NoteForm
        childId={childId}
        childAlias={child.alias}
        basisConfirmed={Boolean(child.sensitive_basis_at)}
        onCreated={reload}
      />
      <AsyncView loading={loading} error={error} onRetry={reload}>
        {data && data.length === 0 && <EmptyState>작성된 메모가 없습니다.</EmptyState>}
        {data && data.length > 0 && (
          <ul className="card-list notes__list">
            {data.map((note) => (
              <li key={note.id}>
                <NoteItem note={note} />
              </li>
            ))}
          </ul>
        )}
      </AsyncView>
    </section>
  );
}
