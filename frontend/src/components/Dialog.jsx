import { useEffect, useId, useRef } from 'react';

// Modal built on the native <dialog> element (focus trap and Escape for free).
// Mount it only while it should be visible. `primaryFirst` lists the main
// button first when the buttons stack on a phone.
export default function Dialog({ title, onClose, actions, primaryFirst = false, children }) {
  const ref = useRef(null);
  const titleId = useId();

  useEffect(() => {
    const node = ref.current;
    if (node && !node.open) node.showModal();
    return () => {
      if (node && node.open) node.close();
    };
  }, []);

  function handleCancel(event) {
    event.preventDefault();
    if (onClose) onClose();
  }

  const actionsClass = primaryFirst
    ? 'dialog__actions dialog__actions--primary-first'
    : 'dialog__actions';

  return (
    <dialog ref={ref} className="dialog" aria-labelledby={titleId} onCancel={handleCancel}>
      <h2 id={titleId}>{title}</h2>
      {children}
      <div className={actionsClass}>{actions}</div>
    </dialog>
  );
}
