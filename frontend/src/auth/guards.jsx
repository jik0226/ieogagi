import { Navigate, Outlet } from 'react-router-dom';
import GenericErrorView from '../components/GenericErrorView.jsx';
import Loading from '../components/Loading.jsx';
import { homePathFor } from './roles.js';
import { useAuth } from './useAuth.js';

function BootState({ status, retry }) {
  if (status === 'loading') {
    return (
      <div className="page page--narrow">
        <Loading label="로그인 상태를 확인하는 중입니다." />
      </div>
    );
  }
  return (
    <div className="page page--narrow">
      <GenericErrorView level={1} onRetry={retry} />
    </div>
  );
}

// Routes that need a signed-in user with one of the given roles. Anyone else
// is sent to /login (anonymous) or to their own home (wrong role).
export function RequireRole({ roles }) {
  const { status, user, retry } = useAuth();

  if (status === 'loading' || status === 'error') {
    return <BootState status={status} retry={retry} />;
  }
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to={homePathFor(user.role)} replace />;
  return <Outlet />;
}

// Login and signup pages: signed-in users are redirected to their home.
export function PublicOnly() {
  const { status, user, retry } = useAuth();

  if (status === 'loading' || status === 'error') {
    return <BootState status={status} retry={retry} />;
  }
  if (user) return <Navigate to={homePathFor(user.role)} replace />;
  return <Outlet />;
}

export function HomeRedirect() {
  const { status, user, retry } = useAuth();

  if (status === 'loading' || status === 'error') {
    return <BootState status={status} retry={retry} />;
  }
  return <Navigate to={user ? homePathFor(user.role) : '/login'} replace />;
}
