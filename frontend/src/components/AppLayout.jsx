import { Outlet } from 'react-router-dom';
import AppHeader from './AppHeader.jsx';

// `variant` picks the layout family: "mentor" is a phone-first single column
// (max 480px), "staff" is a wide PC layout that still works on small screens.
export default function AppLayout({ variant }) {
  return (
    <>
      <AppHeader variant={variant} />
      <main className={`page page--${variant}`}>
        <Outlet />
      </main>
    </>
  );
}
