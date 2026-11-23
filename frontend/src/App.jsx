import { Route, Routes } from 'react-router-dom';
import { HomeRedirect, PublicOnly, RequireRole } from './auth/guards.jsx';
import { useAuth } from './auth/useAuth.js';
import { MENTOR_ROLES, STAFF_ROLES } from './auth/roles.js';
import AppLayout from './components/AppLayout.jsx';
import ScrollToTop from './components/ScrollToTop.jsx';
import LoginPage from './pages/LoginPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';
import SignupPage from './pages/SignupPage.jsx';
import ChildPage from './pages/mentor/ChildPage.jsx';
import MentorHome from './pages/mentor/MentorHome.jsx';
import RecordCorrectPage from './pages/mentor/RecordCorrectPage.jsx';
import RecordNewPage from './pages/mentor/RecordNewPage.jsx';
import StaffPage from './pages/staff/StaffPage.jsx';
import StaffRecordsPage from './pages/staff/StaffRecordsPage.jsx';

export default function App() {
  const { user } = useAuth();
  // Keyed by the signed-in account: when the account changes (log-out, expiry,
  // another log-in) every screen remounts and drops the previous user's data.
  const accountKey = user ? `user-${user.id}` : 'anonymous';
  return (
    <>
      <ScrollToTop />
      <Routes key={accountKey}>
        <Route path="/" element={<HomeRedirect />} />

        <Route element={<PublicOnly />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
        </Route>

        <Route element={<RequireRole roles={MENTOR_ROLES} />}>
          <Route element={<AppLayout variant="mentor" />}>
            <Route path="/mentor" element={<MentorHome />} />
            <Route path="/mentor/children/:childId" element={<ChildPage />} />
            <Route path="/mentor/children/:childId/records/new" element={<RecordNewPage />} />
            <Route path="/mentor/records/:recordId/correct" element={<RecordCorrectPage />} />
          </Route>
        </Route>

        <Route element={<RequireRole roles={STAFF_ROLES} />}>
          <Route element={<AppLayout variant="staff" />}>
            <Route path="/staff" element={<StaffPage />} />
            <Route path="/staff/records" element={<StaffRecordsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  );
}
