import { ApiError } from '../api/client.js';
import { describeError } from '../utils/messages.js';

// Inline error. 403 is shown as a warning with the fixed "no access" wording,
// never as a retryable failure.
export default function ErrorMessage({ error, onRetry }) {
  const forbidden = error instanceof ApiError && error.status === 403;
  return (
    <div className={forbidden ? 'alert alert--warning' : 'alert alert--error'} role="alert">
      <p>{describeError(error)}</p>
      {onRetry && !forbidden && (
        <button type="button" className="btn btn--small" onClick={onRetry}>
          다시 시도
        </button>
      )}
    </div>
  );
}
