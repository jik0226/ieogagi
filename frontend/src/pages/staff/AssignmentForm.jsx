import { useState } from 'react';
import { createAssignment } from '../../api/assignments.js';
import ErrorMessage from '../../components/ErrorMessage.jsx';
import { SelectField, TextField } from '../../components/FormFields.jsx';
import { useMutation } from '../../hooks/useMutation.js';
import { addDays, diffDays, isDateString, todayKst } from '../../utils/date.js';

const MAX_DAYS = 366;

function checkDates(start, end) {
  if (!isDateString(start) || !isDateString(end)) return '시작일과 종료일을 입력해 주세요.';
  if (start > end) return '종료일은 시작일보다 빠를 수 없습니다.';
  if (diffDays(start, end) > MAX_DAYS) return `배정 기간은 최대 ${MAX_DAYS}일입니다.`;
  return '';
}

export default function AssignmentForm({ mentorOptions, childOptions, onCreated }) {
  const [mentorId, setMentorId] = useState('');
  const [childId, setChildId] = useState('');
  const [startDate, setStartDate] = useState(() => todayKst());
  const [endDate, setEndDate] = useState(() => addDays(todayKst(), 90));
  const [errors, setErrors] = useState({});
  const { run, busy, error } = useMutation(createAssignment);

  async function handleSubmit(event) {
    event.preventDefault();
    const found = {
      mentor: mentorId ? '' : '멘토를 선택해 주세요.',
      child: childId ? '' : '아동을 선택해 주세요.',
      dates: checkDates(startDate, endDate),
    };
    setErrors(found);
    if (Object.values(found).some(Boolean)) return;

    const result = await run({
      mentor_id: Number(mentorId),
      child_id: Number(childId),
      start_date: startDate,
      end_date: endDate,
    });
    if (result.ok) {
      setMentorId('');
      setChildId('');
      onCreated();
    }
  }

  return (
    <form className="form card" onSubmit={handleSubmit} aria-labelledby="assignment-form-title" noValidate>
      <h2 id="assignment-form-title">배정 만들기</h2>
      <SelectField
        label="멘토"
        value={mentorId}
        onChange={setMentorId}
        options={mentorOptions}
        placeholder="멘토 선택"
        error={errors.mentor}
        required
      />
      <SelectField
        label="아동"
        value={childId}
        onChange={setChildId}
        options={childOptions}
        placeholder="아동 선택"
        error={errors.child}
        required
      />
      <div className="grid-2">
        <TextField label="시작일" type="date" value={startDate} onChange={setStartDate} required />
        <TextField
          label="종료일"
          type="date"
          value={endDate}
          onChange={setEndDate}
          error={errors.dates}
          required
        />
      </div>
      <p className="meta">
        배정 기간 동안만 멘토가 인계 카드와 기록을 봅니다. 후임 시작일은 전임 마지막 회차 다음 날 ~ 첫
        회차 전으로 정합니다. (최대 {MAX_DAYS}일)
      </p>
      {/* A 409 (overlapping period) is shown right below the dates it is about. */}
      {error && <ErrorMessage error={error} />}
      <div className="form-actions">
        <button type="submit" className="btn btn--primary" disabled={busy}>
          {busy ? '만드는 중…' : '배정 만들기'}
        </button>
      </div>
    </form>
  );
}
