import { useState } from 'react';
import { ApiError } from '../../api/client.js';
import { createNote } from '../../api/notes.js';
import ErrorMessage from '../../components/ErrorMessage.jsx';
import { TextAreaField } from '../../components/FormFields.jsx';
import { useMutation } from '../../hooks/useMutation.js';

const BODY_MAX = 2000;
const SHARE_MAX = 200;

function isBasisRequired(error) {
  return error instanceof ApiError && error.status === 422 && error.code === 'SENSITIVE_BASIS_REQUIRED';
}

// Share text goes first (mentors see it on the hand-over card). The body is
// switched off until the child's sensitive-information basis is confirmed.
export default function NoteForm({ childId, childAlias, basisConfirmed, onCreated }) {
  const [body, setBody] = useState('');
  const [shareText, setShareText] = useState('');
  const [formError, setFormError] = useState('');
  const [basisRequired, setBasisRequired] = useState(false);
  const { run, busy, error } = useMutation(createNote, { skipError: isBasisRequired });

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmedBody = basisConfirmed ? body.trim() : '';
    const trimmedShare = shareText.trim();
    if (!trimmedBody && !trimmedShare) {
      setFormError('공유 문구와 원문 중 하나 이상 입력해 주세요.');
      return;
    }
    setFormError('');
    setBasisRequired(false);

    const result = await run(childId, {
      body: trimmedBody || undefined,
      share_text: trimmedShare || undefined,
    });
    if (result.ok) {
      setBody('');
      setShareText('');
      onCreated();
    } else if (isBasisRequired(result.error)) {
      setBasisRequired(true);
    }
  }

  return (
    <form className="form note-paper note-paper--form" onSubmit={handleSubmit} aria-labelledby="note-form-title" noValidate>
      <p className="note-paper__stamp note-paper__stamp--new" aria-hidden="true">
        새 메모
      </p>
      <h3 id="note-form-title">메모 쓰기</h3>
      <TextAreaField
        label="공유 문구"
        value={shareText}
        onChange={setShareText}
        maxLength={SHARE_MAX}
        rows={2}
        hint="멘토 인계 카드에 보입니다. 건강·가정 내용은 구체적으로 적지 않습니다."
      />
      <TextAreaField
        label="원문"
        value={body}
        onChange={setBody}
        maxLength={BODY_MAX}
        rows={5}
        disabled={!basisConfirmed}
        placeholder={basisConfirmed ? '건강·가정 관련 원문' : undefined}
        hint="담당자·시설장만 볼 수 있고, 암호화되어 저장됩니다."
      />
      {!basisConfirmed && (
        <p className="alert alert--warning">
          {childAlias}: 민감정보 동의·근거가 확인되지 않아 원문을 입력할 수 없습니다. (아동 탭에서 확인)
        </p>
      )}
      {formError && (
        <p className="field__error" role="alert">
          {formError}
        </p>
      )}
      {basisRequired && (
        <p className="alert alert--warning" role="alert">
          민감정보 확인이 되지 않은 아동에게는 원문을 쓸 수 없습니다. 아동 탭에서 &quot;민감정보
          확인&quot;을 먼저 해 주세요.
        </p>
      )}
      {error && <ErrorMessage error={error} />}
      <div className="form-actions">
        <button type="submit" className="btn btn--primary" disabled={busy}>
          {busy ? '저장 중…' : '메모 저장'}
        </button>
      </div>
    </form>
  );
}
