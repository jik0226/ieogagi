// Empty list message. `title` is the short sentence, children the hint on
// what to do next. `boxed` draws it as a soft card (used on the mentor home).
export default function EmptyState({ title, boxed = false, children }) {
  return (
    <div className={boxed ? 'state state--box' : 'state'}>
      {title && <p className="state__title">{title}</p>}
      {children && <p>{children}</p>}
    </div>
  );
}
