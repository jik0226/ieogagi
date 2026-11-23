import { useState } from 'react';
import { getNote } from '../../api/notes.js';
import ErrorMessage from '../../components/ErrorMessage.jsx';
import { useMutation } from '../../hooks/useMutation.js';
import { formatDateOnly, formatDateTime } from '../../utils/date.js';

export default function NoteItem({ note }) {
  const [revealed, setRevealed] = useState(null);
  const { run, busy, error, reset } = useMutation(getNote);

  async function handleReveal() {
    const result = await run(note.id);
    if (result.ok) setRevealed(result.data);
  }

  function handleHide() {
    setRevealed(null);
    reset();
  }

  return (
    <article className="note-paper">
      <p className="note-paper__stamp">
        <time dateTime={note.created_at}>{formatDateOnly(note.created_at)}</time>
      </p>
      <p className="note-paper__label">공유 문구</p>
      <p className="note-paper__text pre-wrap">{note.share_text || '공유 문구 없음'}</p>
      {revealed && (
        <div className="note-paper__original">
          <h3>원문</h3>
          <p className="pre-wrap">{revealed.body ?? '원문이 없습니다.'}</p>
        </div>
      )}
      {error && <ErrorMessage error={error} />}
      <footer className="note-paper__foot">
        <span className={note.has_body ? 'note-paper__tag note-paper__tag--body' : 'note-paper__tag'}>
          {note.has_body ? '원문 있음' : '공유 문구만'}
        </span>
        <span className="note-paper__by">
          {note.author.display_name} · {formatDateTime(note.created_at)}
        </span>
      </footer>
      {note.has_body && (
        <div className="note-paper__reveal">
          {revealed ? (
            <button type="button" className="btn btn--small" onClick={handleHide}>
              원문 닫기
            </button>
          ) : (
            <button type="button" className="btn btn--small" onClick={handleReveal} disabled={busy}>
              {busy ? '불러오는 중…' : '원문 보기'}
            </button>
          )}
          <p className="note-paper__hint">원문을 열면 누가 언제 봤는지 감사 로그에 남습니다.</p>
        </div>
      )}
    </article>
  );
}
