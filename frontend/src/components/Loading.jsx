// Grey placeholder bars while data loads. The visible label keeps the state
// readable for people who do not see the animation.
export default function Loading({ label = '불러오는 중입니다.', cards = 2 }) {
  const placeholders = Array.from({ length: cards }, (_, index) => index);

  return (
    <div className="skeleton" role="status" aria-live="polite">
      <div className="skeleton__bar skeleton__bar--title" aria-hidden="true" />
      <div className="skeleton__bar" aria-hidden="true" />
      <div className="skeleton__bar skeleton__bar--wide" aria-hidden="true" />
      {placeholders.map((index) => (
        <div key={index} className="skeleton__card" aria-hidden="true">
          <div className="skeleton__bar" />
          <div className="skeleton__bar skeleton__bar--medium" />
        </div>
      ))}
      <p className="skeleton__label">{label}</p>
    </div>
  );
}
