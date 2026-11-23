import ErrorMessage from './ErrorMessage.jsx';
import ErrorState from './ErrorState.jsx';
import Loading from './Loading.jsx';

// Renders the loading and error states of a useAsync result; the page only
// supplies the "ready" content as children. With `screen`, a failure takes
// over the whole area (blocked / error screen) instead of an inline message.
// `cards` sets how many placeholder cards the loading skeleton draws.
export default function AsyncView({ loading, error, onRetry, screen = false, cards, children }) {
  if (loading) return <Loading cards={cards} />;
  if (error) {
    return screen ? (
      <ErrorState error={error} onRetry={onRetry} />
    ) : (
      <ErrorMessage error={error} onRetry={onRetry} />
    );
  }
  return children;
}
