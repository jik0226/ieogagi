import { sensitiveCategoryLabels } from '../utils/labels.js';
import Dialog from './Dialog.jsx';

function dialogTitle(categories) {
  const labels = sensitiveCategoryLabels(categories);
  if (labels.length === 0) return '민감한 내용이 있는 것 같아요';
  return `${labels.join('·')} 관련 내용이 있는 것 같아요`;
}

// Shown when the server answers 422 SENSITIVE_CONFIRM_REQUIRED. "수정하기" is
// the main button; Escape also means "수정하기".
export default function SensitiveConfirmDialog({ categories, busy, onEdit, onSaveAnyway }) {
  const actions = (
    <>
      <button type="button" className="btn btn--primary" onClick={onEdit} disabled={busy}>
        수정하기
      </button>
      <button type="button" className="btn" onClick={onSaveAnyway} disabled={busy}>
        그래도 저장
      </button>
    </>
  );

  return (
    <Dialog title={dialogTitle(categories)} onClose={onEdit} actions={actions} primaryFirst>
      <p>
        기록은 다음 선생님에게도 전해집니다. 학습 내용만 남겼는지 확인해 주세요. 건강·가정 정보는 담당
        선생님께 직접 알려 주세요.
      </p>
    </Dialog>
  );
}
