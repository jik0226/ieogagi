import { isStatus } from '../utils/messages.js';
import ForbiddenView from './ForbiddenView.jsx';
import GenericErrorView from './GenericErrorView.jsx';

// Full-screen result of a failed load: 403 gets the blocked screen,
// everything else the generic "try again" screen.
export default function ErrorState({ error, onRetry }) {
  if (isStatus(error, 403)) return <ForbiddenView />;
  return <GenericErrorView onRetry={onRetry} />;
}
