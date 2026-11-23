import { useId, useState } from 'react';
import { SelectField, TextField } from '../../components/FormFields.jsx';
import { AUDIT_ACTIONS, auditActionLabel } from '../../utils/auditLabels.js';
import { AUDIT_RESULTS, auditResult } from '../../utils/labels.js';

const ACTION_OPTIONS = AUDIT_ACTIONS.map((action) => ({
  value: action,
  label: `${auditActionLabel(action)} (${action})`,
}));
const RESULT_CHIPS = [
  { value: '', label: '전체' },
  ...AUDIT_RESULTS.map((result) => ({ value: result, label: auditResult(result).label })),
];
const EMPTY = { action: '', result: '', dateFrom: '', dateTo: '' };

// Filters: result as pill chips (radio buttons), then action, a date range
// (Korean dates, both ends included) and the search buttons. A result chip
// applies at once (with the other fields as they stand); the rest wait for 조회.
export default function AuditFilters({ initial, onApply }) {
  const [draft, setDraft] = useState(initial);
  const [formError, setFormError] = useState('');
  const radioName = useId();

  function update(name, value) {
    setDraft((current) => ({ ...current, [name]: value }));
  }

  // Shared by the 조회 button and the result chips.
  function apply(next) {
    if (next.dateFrom && next.dateTo && next.dateFrom > next.dateTo) {
      setFormError('시작 날짜는 끝 날짜보다 늦을 수 없습니다.');
      return;
    }
    setFormError('');
    onApply(next);
  }

  function handleSubmit(event) {
    event.preventDefault();
    apply(draft);
  }

  function handleResultChange(value) {
    const next = { ...draft, result: value };
    setDraft(next);
    apply(next);
  }

  function handleReset() {
    setDraft(EMPTY);
    setFormError('');
    onApply(EMPTY);
  }

  return (
    <form className="card audit-filter" onSubmit={handleSubmit} aria-label="감사 로그 조회 조건" noValidate>
      <div className="audit-filter__head">
        <h2 className="audit-filter__title">기록 찾기</h2>
        <fieldset className="audit-filter__results">
          <legend className="visually-hidden">결과 (고르면 바로 조회됩니다)</legend>
          {RESULT_CHIPS.map((chip) => (
            <label key={chip.value || 'all'} className="chip">
              <input
                type="radio"
                className="chip__input"
                name={radioName}
                value={chip.value}
                checked={draft.result === chip.value}
                onChange={() => handleResultChange(chip.value)}
              />
              <span className="chip__text">{chip.label}</span>
            </label>
          ))}
        </fieldset>
      </div>
      <div className="audit-filter__row">
        <SelectField
          label="동작"
          value={draft.action}
          onChange={(value) => update('action', value)}
          options={ACTION_OPTIONS}
          placeholder="전체"
        />
        <fieldset className="audit-filter__period">
          <legend className="audit-filter__legend">기간</legend>
          <div className="audit-filter__range">
            <TextField
              label="시작 날짜"
              type="date"
              value={draft.dateFrom}
              onChange={(value) => update('dateFrom', value)}
            />
            <span className="audit-filter__tilde" aria-hidden="true">
              ~
            </span>
            <TextField
              label="끝 날짜"
              type="date"
              value={draft.dateTo}
              onChange={(value) => update('dateTo', value)}
              error={formError}
            />
          </div>
        </fieldset>
        <div className="filter-row__buttons">
          <button type="submit" className="btn btn--primary">
            조회
          </button>
          <button type="button" className="btn" onClick={handleReset}>
            초기화
          </button>
        </div>
      </div>
    </form>
  );
}
