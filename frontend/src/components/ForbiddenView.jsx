import { Link } from 'react-router-dom';
import { FORBIDDEN_TEXT, FORBIDDEN_TITLE } from '../utils/messages.js';

// Full-screen block shown whenever a mentor's request is refused (403).
// The wording is fixed and never says why, so a refusal does not reveal
// whether an assignment exists or when it ended.
export default function ForbiddenView({ level = 2 }) {
  const Heading = level === 1 ? 'h1' : 'h2';

  return (
    <section className="state-screen state-screen--blocked" role="alert">
      <p className="state-screen__icon" aria-hidden="true">
        ⛔
      </p>
      <Heading className="state-screen__title">{FORBIDDEN_TITLE}</Heading>
      <p className="state-screen__text">{FORBIDDEN_TEXT}</p>
      <Link className="btn" to="/mentor">
        내 아동으로
      </Link>
    </section>
  );
}
