import { useAuth } from '../auth/useAuth.js';
import { roleLabel } from '../utils/labels.js';

// Greeting block at the top of the staff pages: who is signed in, then the
// page title. The overlapping circles are drawn in CSS (decoration only).
export default function StaffHero({ title }) {
  const { user } = useAuth();

  return (
    <section className="staff-hero">
      <p className="staff-hero__hello">안녕하세요, {user.display_name} 님</p>
      <h1>{title}</h1>
      <p className="staff-hero__where">
        {user.center.name} · {roleLabel(user.role)}
      </p>
    </section>
  );
}
