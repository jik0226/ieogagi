import { useState } from 'react';
import Dialog from './Dialog.jsx';
import ErrorMessage from './ErrorMessage.jsx';
import { TextField } from './FormFields.jsx';

// Generic confirmation. Cancel is always on the left, the action on the
// right. Pass `requireText` to force the user to type an exact phrase before
// the confirm button unlocks (used for irreversible actions).
export default function ConfirmDialog({
  title,
  children,
  confirmLabel = '확인',
  danger = false,
  requireText,
  requireLabel = '확인용 입력',
  requireHint = '같은 글자를 정확히 입력해야 진행할 수 있습니다.',
  busy = false,
  error = null,
  onConfirm,
  onCancel,
}) {
  const [typed, setTyped] = useState('');
  const needsTyping = requireText !== undefined;
  const locked = needsTyping && typed !== requireText;

  function handleClose() {
    if (!busy) onCancel();
  }

  // Cancel takes the first focus on dangerous actions without typing, so a
  // stray Enter key does not confirm them.
  const actions = (
    <>
      <button
        type="button"
        className="btn"
        onClick={onCancel}
        disabled={busy}
        autoFocus={danger && !needsTyping}
      >
        취소
      </button>
      <button
        type="button"
        className={danger ? 'btn btn--danger' : 'btn btn--primary'}
        onClick={onConfirm}
        disabled={busy || locked}
      >
        {confirmLabel}
      </button>
    </>
  );

  return (
    <Dialog title={title} onClose={handleClose} actions={actions}>
      <div className="stack">
        {children}
        {needsTyping && (
          <TextField
            label={requireLabel}
            value={typed}
            onChange={setTyped}
            maxLength={40}
            autoComplete="off"
            hint={locked ? requireHint : undefined}
          />
        )}
        {error && <ErrorMessage error={error} />}
      </div>
    </Dialog>
  );
}
