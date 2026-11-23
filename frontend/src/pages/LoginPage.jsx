import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/useAuth.js';
import ErrorMessage from '../components/ErrorMessage.jsx';
import { TextField } from '../components/FormFields.jsx';
import { useMutation } from '../hooks/useMutation.js';
import { SESSION_EXPIRED_MESSAGE } from '../utils/messages.js';

// Same allow-list as the server's LoginId; checked here only to explain the
// format (an e-mail address is the usual mistake), never to probe accounts.
const LOGIN_ID_PATTERN = /^[a-z0-9_]{4,32}$/;
const LOGIN_ID_HINT = '아이디는 영어 소문자·숫자·밑줄(_) 4~32자입니다. 이메일 주소가 아니라 가입할 때 만든 아이디를 넣어 주세요.';

export default function LoginPage() {
  const { login, expired } = useAuth();
  const location = useLocation();
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [idError, setIdError] = useState('');
  const { run, busy, error } = useMutation(login);
  const justSignedUp = location.state?.signedUp === true;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!loginId.trim() || !password) {
      setFormError('아이디와 비밀번호를 입력해 주세요.');
      return;
    }
    setFormError('');
    if (!LOGIN_ID_PATTERN.test(loginId.trim())) {
      setIdError(LOGIN_ID_HINT);
      return;
    }
    setIdError('');
    // On success the auth context stores the user and the route guard
    // redirects to the role's home page.
    await run({ login_id: loginId.trim(), password });
  }

  return (
    <div className="page page--narrow stack auth-page login-page">
      <div className="brand-block">
        <h1>이어가기</h1>
        <p className="meta">지역아동센터 교육봉사 인계 수첩</p>
      </div>
      {expired && !error && (
        <div className="alert alert--warning" role="alert">
          {SESSION_EXPIRED_MESSAGE}
        </div>
      )}
      {justSignedUp && (
        <div className="alert alert--success" role="status">
          가입이 끝났습니다. 로그인해 주세요.
        </div>
      )}
      <form className="form card" onSubmit={handleSubmit} aria-label="로그인" noValidate>
        {error && <ErrorMessage error={error} />}
        <TextField
          label="아이디"
          value={loginId}
          onChange={setLoginId}
          error={idError}
          maxLength={32}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
        />
        <TextField
          label="비밀번호"
          type="password"
          value={password}
          onChange={setPassword}
          maxLength={128}
          autoComplete="current-password"
          required
        />
        {formError && (
          <p className="field__error" role="alert">
            {formError}
          </p>
        )}
        <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
          {busy ? '로그인 중…' : '로그인'}
        </button>
      </form>
      <p className="meta">
        초대 코드가 있나요?{' '}
        <Link className="tap-link" to="/signup">
          초대 코드로 가입하기
        </Link>
      </p>
    </div>
  );
}
