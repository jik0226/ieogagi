import { useState } from 'react';
import { hideRecord } from '../../api/records.js';
import Dialog from '../../components/Dialog.jsx';
import ErrorMessage from '../../components/ErrorMessage.jsx';
import { RadioGroupField } from '../../components/FormFields.jsx';
import { useMutation } from '../../hooks/useMutation.js';
import { formatDate } from '../../utils/date.js';
import { HIDE_REASON_OPTIONS } from '../../utils/labels.js';

export default function HideDialog({ record, onClose, onDone }) {
  const [reason, setReason] = useState('');
  const [formError, setFormError] = useState('');
  const { run, busy, error } = useMutation(hideRecord);

  async function handleConfirm() {
    if (!reason) {
      setFormError('숨기는 사유를 선택해 주세요.');
      return;
    }
    setFormError('');
    const result = await run(record.id, reason);
    if (result.ok) onDone();
  }

  const actions = (
    <>
      <button type="button" className="btn" onClick={onClose} disabled={busy}>
        취소
      </button>
      <button type="button" className="btn btn--danger" onClick={handleConfirm} disabled={busy}>
        {busy ? '처리 중…' : '숨기기'}
      </button>
    </>
  );

  return (
    <Dialog title="기록 숨기기" onClose={busy ? undefined : onClose} actions={actions}>
      <div className="stack">
        <p>숨긴 기록은 멘토 화면과 인계 카드에서 빠지고, 담당자 화면에는 사유와 함께 남습니다.</p>
        <p className="meta">
          {formatDate(record.session_date)} 기록
          {record.corrects_id !== null && ' · 정정본을 숨기면 원래 기록이 다시 보입니다.'}
        </p>
        <RadioGroupField
          legend="숨기는 사유"
          value={reason}
          onChange={setReason}
          options={HIDE_REASON_OPTIONS}
          error={formError}
        />
        {error && <ErrorMessage error={error} />}
      </div>
    </Dialog>
  );
}
