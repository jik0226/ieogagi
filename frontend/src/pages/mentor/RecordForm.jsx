import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../../api/client.js';
import ErrorMessage from '../../components/ErrorMessage.jsx';
import ForbiddenView from '../../components/ForbiddenView.jsx';
import { TextAreaField, TextField } from '../../components/FormFields.jsx';
import SensitiveConfirmDialog from '../../components/SensitiveConfirmDialog.jsx';
import { useMutation } from '../../hooks/useMutation.js';
import { formatPeriod } from '../../utils/date.js';
import { recordFieldEntries } from '../../utils/labels.js';
import {
  ALREADY_CORRECTED_MESSAGE,
  invalidFieldNames,
  isStatus,
} from '../../utils/messages.js';
import { checkRecordFields } from '../../utils/validators.js';

const FIELD_MAX_LENGTH = 500;
const RECHECK_MESSAGE = '입력 값을 다시 확인해 주세요.';
const DATE_RANGE_MESSAGE = '회차 날짜는 배정 기간 안이면서 오늘 이전이어야 합니다.';

function isSensitiveConfirmError(error) {
  return (
    error instanceof ApiError && error.status === 422 && error.code === 'SENSITIVE_CONFIRM_REQUIRED'
  );
}

// Shared by "new record" and "correction". In correction mode the date is
// fixed (the contract does not accept session_date for corrections) and the
// original record is shown by the page above the form.
export default function RecordForm({ mode, initial, minDate, maxDate, submitRecord, backTo }) {
  const navigate = useNavigate();
  const isCorrection = mode === 'correct';
  const [sessionDate, setSessionDate] = useState(initial.session_date);
  const [fields, setFields] = useState({
    did: initial.did,
    stuck: initial.stuck,
    next_step: initial.next_step,
  });
  const [formError, setFormError] = useState('');
  const [dateError, setDateError] = useState('');
  const [sensitiveCategories, setSensitiveCategories] = useState(null);
  const { run, busy, error } = useMutation(submitRecord, { skipError: isSensitiveConfirmError });
  const serverFields = invalidFieldNames(error);

  // The period ended or was revoked while the form was open: blocked screen.
  if (isStatus(error, 403)) return <ForbiddenView />;

  // Only a confirmed success leaves the page; on any failure (including an
  // unreadable response) the typed fields stay as they are.
  async function send(confirmed) {
    const result = await run({ session_date: sessionDate, ...fields, sensitive_confirmed: confirmed });
    if (result.ok) {
      navigate(backTo, { replace: true, state: { saved: true } });
    } else if (isSensitiveConfirmError(result.error)) {
      setSensitiveCategories(result.error.categories);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    let problem = '';
    if (!isCorrection) {
      const outOfRange = !sessionDate || sessionDate < minDate || sessionDate > maxDate;
      problem = outOfRange ? DATE_RANGE_MESSAGE : '';
    }
    setDateError(problem);
    const fieldsProblem = checkRecordFields(fields);
    setFormError(fieldsProblem);
    if (problem || fieldsProblem) return;
    await send(false);
  }

  function handleSaveAnyway() {
    setSensitiveCategories(null);
    return send(true);
  }

  const alreadyCorrected = isStatus(error, 409);
  const dateMessage = dateError || (serverFields.has('session_date') ? DATE_RANGE_MESSAGE : '');

  return (
    <form className="form card record-form" onSubmit={handleSubmit} aria-label="회차 기록" noValidate>
      {/* Kept at the top: the fixed save button used to cover it at the bottom. */}
      <p className="alert alert--warning record-form__note" role="note">
        학습 내용만 적어 주세요. 건강·가정 관련 내용은 적지 않습니다.
      </p>

      {!isCorrection && (
        <TextField
          label="수업 날짜"
          type="date"
          name="session_date"
          value={sessionDate}
          onChange={setSessionDate}
          min={minDate}
          max={maxDate}
          hint={`고를 수 있는 날짜: ${formatPeriod(minDate, maxDate)}`}
          error={dateMessage}
          required
        />
      )}

      {recordFieldEntries(fields).map((field) => (
        <TextAreaField
          key={field.name}
          name={field.name}
          label={field.label}
          value={field.value}
          onChange={(value) => setFields((current) => ({ ...current, [field.name]: value }))}
          maxLength={FIELD_MAX_LENGTH}
          rows={4}
          error={serverFields.has(field.name) ? RECHECK_MESSAGE : ''}
        />
      ))}

      <p className="field__hint">
        세 칸 중 하나 이상 적어 주세요.
        {isCorrection && ' 원래 기록은 지워지지 않고, 정정본이 새로 저장됩니다.'}
      </p>

      {formError && (
        <p className="field__error" role="alert">
          {formError}
        </p>
      )}
      {alreadyCorrected && (
        <div className="alert alert--error" role="alert">
          {ALREADY_CORRECTED_MESSAGE}
        </div>
      )}
      {error && !alreadyCorrected && <ErrorMessage error={error} />}

      <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
        {busy ? '저장 중…' : isCorrection ? '정정 저장' : '저장'}
      </button>
      <button type="button" className="btn btn--block" onClick={() => navigate(backTo)} disabled={busy}>
        취소
      </button>

      {sensitiveCategories && (
        <SensitiveConfirmDialog
          categories={sensitiveCategories}
          busy={busy}
          onEdit={() => setSensitiveCategories(null)}
          onSaveAnyway={handleSaveAnyway}
        />
      )}
    </form>
  );
}
