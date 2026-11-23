// Wide tables scroll sideways inside this box on small screens. The box is a
// named, focusable region so keyboard users can scroll it too.
export default function ScrollTable({ label, children }) {
  return (
    <div className="table-wrap" role="region" aria-label={label} tabIndex={0}>
      {children}
    </div>
  );
}
