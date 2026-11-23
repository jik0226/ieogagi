// Full-screen "something went wrong". No error text, code or location is
// ever shown here.
export default function GenericErrorView({ onRetry, level = 2 }) {
  const Heading = level === 1 ? 'h1' : 'h2';

  return (
    <section className="state-screen" role="alert">
      <Heading className="state-screen__title">문제가 생겼습니다</Heading>
      <p className="state-screen__text">잠시 후 다시 시도해 주세요.</p>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          다시 시도
        </button>
      )}
    </section>
  );
}
