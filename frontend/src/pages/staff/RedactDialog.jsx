import { useState } from 'react';
import { redactRecord } from '../../api/records.js';
import Dialog from '../../components/Dialog.jsx';
import ErrorMessage from '../../components/ErrorMessage.jsx';
import { CheckboxField } from '../../components/FormFields.jsx';
import { useMutation } from '../../hooks/useMutation.js';
import { formatDate } from '../../utils/date.js';
import { recordFieldEntries } from '../../utils/labels.js';

export default function RedactDialog({ record, onClose, onDone }) {
  const [selected, setSelected] = useState([]);
  const [formError, setFormError] = useState('');
  const { run, busy, error } = useMutation(redactRecord);

  function toggle(name, checked) {
    setSelected((current) => (checked ? [...current, name] : current.filter((item) => item !== name)));
  }

  async function handleConfirm() {
    if (selected.length === 0) {
      setFormError('지울 칸을 하나 이상 선택해 주세요.');
      return;
    }
    setFormError('');
    const result = await run(record.id, selected);
    if (result.ok) onDone();
  }

  const actions = (
    <>
      <button type="button" className="btn" onClick={onClose} disabled={busy}>
        취소
      </button>
      <button type="button" className="btn btn--danger" onClick={handleConfirm} disabled={busy}>
        {busy ? '처리 중…' : '지우기'}
      </button>
    </>
  );

  return (
    <Dialog title="민감정보 칸 지우기" onClose={busy ? undefined : onClose} actions={actions}>
      <div className="stack">
        <p>고른 칸의 내용만 지웁니다. 기록 행과 감사 기록은 남습니다.</p>
        <p className="alert alert--warning">
          <strong>지운 내용은 되돌릴 수 없습니다.</strong> ({formatDate(record.session_date)} 기록)
        </p>
        <fieldset className="field">
          <legend>지울 칸</legend>
          {recordFieldEntries(record, { past: true }).map((field) => (
            <CheckboxField
              key={field.name}
              label={field.label}
              checked={selected.includes(field.name)}
              onChange={(checked) => toggle(field.name, checked)}
            />
          ))}
        </fieldset>
        {formError && (
          <p className="field__error" role="alert">
            {formError}
          </p>
        )}
        {error && <ErrorMessage error={error} />}
      </div>
    </Dialog>
  );
}
