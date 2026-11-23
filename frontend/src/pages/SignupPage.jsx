import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signup, verifyInvite } from '../api/auth.js';
import { ApiError } from '../api/client.js';
import ErrorMessage from '../components/ErrorMessage.jsx';
import { TextField } from '../components/FormFields.jsx';
import { useMutation } from '../hooks/useMutation.js';
import { formatDateTime } from '../utils/date.js';
import { inviteRoleLabel } from '../utils/labels.js';
import { invalidFieldNames } from '../utils/messages.js';
import { checkDisplayName, checkLoginId, checkNewPassword } from '../utils/validators.js';

const RECHECK_MESSAGE = '입력 값을 다시 확인해 주세요.';

// Step 1: check the invite code. A valid code shows centre, role and expiry
// before the person moves on.
function InviteStep({ onNext }) {
  const [code, setCode] = useState('');
  const [invite, setInvite] = useState(null);
  const [formError, setFormError] = useState('');
  const { run, busy, error, reset } = useMutation(verifyInvite);

  function handleChange(value) {
    setCode(value);
    setInvite(null);
    reset();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (invite) {
      onNext(code.trim());
      return;
    }
    const trimmed = code.trim();
    if (!trimmed) {
      setFormError('초대 코드를 입력해 주세요.');
      return;
    }
    setFormError('');
    const result = await run(trimmed);
    if (result.ok) setInvite(result.data);
  }

  return (
    <form className="form card" onSubmit={handleSubmit} aria-label="초대 코드 확인" noValidate>
      {error && <ErrorMessage error={error} />}
      <TextField
        label="초대 코드"
        value={code}
        onChange={handleChange}
        placeholder="센터에서 받은 코드"
        maxLength={64}
        autoComplete="off"
        autoCapitalize="none"
        spellCheck={false}
        error={formError}
        required
      />
      {invite ? (
        <>
          <div className="alert alert--success" role="status">
            <p>
              <strong>{invite.center_name}</strong> · {inviteRoleLabel(invite.role)} 초대되었습니다
            </p>
            <p className="meta">코드 유효: {formatDateTime(invite.expires_at)}까지</p>
          </div>
          <button type="submit" className="btn btn--primary btn--block">
            다음
          </button>
        </>
      ) : (
        <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
          {busy ? '확인 중…' : '코드 확인'}
        </button>
      )}
    </form>
  );
}

// Step 2: choose login id, name and password.
function AccountStep({ code, onBack }) {
  const navigate = useNavigate();
  const [loginId, setLoginId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [repeat, setRepeat] = useState('');
  const [errors, setErrors] = useState({});
  const { run, busy, error } = useMutation(signup);
  const serverFields = invalidFieldNames(error);
  const duplicateId = error instanceof ApiError && error.status === 409;
  const serverMessage =
    error instanceof ApiError && error.hasServerMessage ? error.message : RECHECK_MESSAGE;
  // Errors that belong to a specific field are shown under it, not in a box.
  const fieldLevel = duplicateId || serverFields.size > 0;

  async function handleSubmit(event) {
    event.preventDefault();
    const found = {
      login_id: checkLoginId(loginId),
      display_name: checkDisplayName(displayName),
      password: checkNewPassword(password),
      repeat: password === repeat ? '' : '비밀번호가 서로 다릅니다.',
    };
    setErrors(found);
    if (Object.values(found).some(Boolean)) return;

    const result = await run({
      code,
      login_id: loginId,
      display_name: displayName.trim(),
      password,
    });
    // No automatic login after signup: go to the login screen.
    if (result.ok) navigate('/login', { replace: true, state: { signedUp: true } });
  }

  const serverHint = (name) => (serverFields.has(name) ? RECHECK_MESSAGE : '');
  const loginIdError = errors.login_id || (duplicateId ? serverMessage : serverHint('login_id'));
  const passwordError =
    errors.password || (serverFields.has('password') ? serverMessage : '');

  return (
    <form className="form card" onSubmit={handleSubmit} aria-label="계정 만들기" noValidate>
      <TextField
        label="아이디"
        value={loginId}
        onChange={setLoginId}
        placeholder="영문 소문자·숫자·_ 4~32자"
        maxLength={32}
        autoComplete="username"
        autoCapitalize="none"
        spellCheck={false}
        error={loginIdError}
        required
      />
      <TextField
        label="이름"
        value={displayName}
        onChange={setDisplayName}
        placeholder="센터에서 부를 이름 (30자)"
        maxLength={30}
        autoComplete="name"
        error={errors.display_name || serverHint('display_name')}
        required
      />
      <TextField
        label="비밀번호"
        type="password"
        value={password}
        onChange={setPassword}
        maxLength={128}
        autoComplete="new-password"
        hint="10자 이상. 영문 대문자·소문자·숫자·특수문자 중 2종류 이상"
        error={passwordError}
        required
      />
      <TextField
        label="비밀번호 확인"
        type="password"
        value={repeat}
        onChange={setRepeat}
        maxLength={128}
        autoComplete="new-password"
        error={errors.repeat}
        required
      />
      {error && !fieldLevel && <ErrorMessage error={error} />}
      <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
        {busy ? '가입 중…' : '가입하기'}
      </button>
      <button type="button" className="btn btn--block" onClick={onBack} disabled={busy}>
        코드 다시 입력
      </button>
    </form>
  );
}

export default function SignupPage() {
  const [verified, setVerified] = useState(null);

  return (
    <div className="page page--narrow stack auth-page signup-page">
      <h1>
        초대 코드로 가입 <span className="stepper">{verified ? '2/2' : '1/2'}</span>
      </h1>
      {verified ? (
        <AccountStep code={verified.code} onBack={() => setVerified(null)} />
      ) : (
        <InviteStep onNext={(code) => setVerified({ code })} />
      )}
      <p className="meta">
        이미 계정이 있나요?{' '}
        <Link className="tap-link" to="/login">
          로그인하기
        </Link>
      </p>
    </div>
  );
}
