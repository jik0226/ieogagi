import { useState } from 'react';
import { createChild } from '../../api/children.js';
import ErrorMessage from '../../components/ErrorMessage.jsx';
import { CheckboxField, SelectField, TextField } from '../../components/FormFields.jsx';
import { useMutation } from '../../hooks/useMutation.js';
import { GRADES } from '../../utils/labels.js';
import { invalidFieldNames } from '../../utils/messages.js';

const GRADE_OPTIONS = GRADES.map((grade) => ({ value: grade, label: grade }));

// Register a child. The button stays off until the privacy consent box is
// ticked, and the reason is written next to it. There are deliberately no
// fields for birth date, address or phone number.
export default function ChildForm({ onCreated }) {
  const [alias, setAlias] = useState('');
  const [grade, setGrade] = useState('');
  const [privacyConfirmed, setPrivacyConfirmed] = useState(false);
  const [sensitiveConfirmed, setSensitiveConfirmed] = useState(false);
  const [errors, setErrors] = useState({});
  const { run, busy, error } = useMutation(createChild);
  const serverFields = invalidFieldNames(error);

  async function handleSubmit(event) {
    event.preventDefault();
    const found = {
      alias: alias.trim() ? '' : '별칭을 입력해 주세요.',
      grade: grade ? '' : '학년을 선택해 주세요.',
    };
    setErrors(found);
    if (Object.values(found).some(Boolean)) return;

    const result = await run({
      alias: alias.trim(),
      grade,
      privacy_consent_confirmed: true,
      sensitive_basis_confirmed: sensitiveConfirmed,
    });
    if (result.ok) {
      setAlias('');
      setGrade('');
      setPrivacyConfirmed(false);
      setSensitiveConfirmed(false);
      onCreated();
    }
  }

  return (
    <form
      id="child-form"
      className="form card"
      onSubmit={handleSubmit}
      aria-labelledby="child-form-title"
      noValidate
    >
      <h2 id="child-form-title">아동 등록</h2>
      <TextField
        label="별칭"
        value={alias}
        onChange={setAlias}
        placeholder="실명 대신 센터 안에서만 쓰는 별칭 (20자)"
        maxLength={20}
        autoComplete="off"
        error={errors.alias || (serverFields.has('alias') ? '별칭을 다시 확인해 주세요.' : '')}
        required
      />
      <SelectField
        label="학년"
        value={grade}
        onChange={setGrade}
        options={GRADE_OPTIONS}
        placeholder="선택"
        error={errors.grade}
        required
      />
      <CheckboxField
        label="개인정보 처리 동의를 확인했습니다. (필수 · 만 14세 미만은 법정대리인)"
        checked={privacyConfirmed}
        onChange={setPrivacyConfirmed}
      />
      <CheckboxField
        label="민감정보(건강 등) 별도 동의 또는 법령상 근거를 확인했습니다. (선택)"
        checked={sensitiveConfirmed}
        onChange={setSensitiveConfirmed}
        hint="지금 확인하지 않아도 되고, 나중에 목록에서 '민감정보 확인'을 눌러 기록할 수 있습니다."
      />
      {error && <ErrorMessage error={error} />}
      <div className="form-actions">
        <button type="submit" className="btn btn--primary" disabled={busy || !privacyConfirmed}>
          {busy ? '등록 중…' : '등록'}
        </button>
        {!privacyConfirmed && (
          <p className="form-actions__reason">개인정보 처리 동의를 확인하면 등록할 수 있습니다.</p>
        )}
      </div>
    </form>
  );
}
