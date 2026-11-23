import { useCallback, useState } from 'react';
import { confirmSensitiveBasis, destroyChild, listChildren } from '../../api/children.js';
import AsyncView from '../../components/AsyncView.jsx';
import ConfirmDialog from '../../components/ConfirmDialog.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { useAuth } from '../../auth/useAuth.js';
import { useAsync } from '../../hooks/useAsync.js';
import { useMutation } from '../../hooks/useMutation.js';
import { objectParticle } from '../../utils/josa.js';
import ChildForm from './ChildForm.jsx';
import ChildrenTable from './ChildrenTable.jsx';

// `onChanged` tells the page that something the "확인이 필요한 항목" counts
// depend on was saved. The registration form stays closed until "아동 등록"
// is pressed, so the first screen shows the list rather than an empty form.
// It stays open after a save, for registering several children in a row.
export default function ChildrenTab({ onChanged }) {
  const { user } = useAuth();
  const isDirector = user.role === 'director';
  const load = useCallback(() => listChildren(), []);
  const { loading, data, error, reload } = useAsync(load);
  const [basisTarget, setBasisTarget] = useState(null);
  const [destroyTarget, setDestroyTarget] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const basis = useMutation(confirmSensitiveBasis);
  const destroy = useMutation(destroyChild);

  async function handleBasis() {
    const result = await basis.run(basisTarget.id);
    if (result.ok) {
      setBasisTarget(null);
      reload();
      onChanged();
    }
  }

  async function handleDestroy() {
    const result = await destroy.run(destroyTarget.id);
    if (result.ok) {
      setDestroyTarget(null);
      reload();
      onChanged();
    }
  }

  function handleCreated() {
    reload();
    onChanged();
  }

  function closeBasis() {
    basis.reset();
    setBasisTarget(null);
  }

  function closeDestroy() {
    destroy.reset();
    setDestroyTarget(null);
  }

  return (
    <div className={formOpen ? 'split split--aside' : undefined}>
      {formOpen && <ChildForm onCreated={handleCreated} />}
      <section className="stack" aria-labelledby="children-title">
        <div className="row row--between">
          <h2 id="children-title">등록된 아동</h2>
          <button
            type="button"
            className={formOpen ? 'btn' : 'btn btn--primary'}
            aria-expanded={formOpen}
            aria-controls={formOpen ? 'child-form' : undefined}
            onClick={() => setFormOpen((open) => !open)}
          >
            {formOpen ? '등록 양식 닫기' : '아동 등록'}
          </button>
        </div>
        <AsyncView loading={loading} error={error} onRetry={reload}>
          {data && data.length === 0 && <EmptyState>등록된 아동이 없습니다.</EmptyState>}
          {data && data.length > 0 && (
            <ChildrenTable
              items={data}
              isDirector={isDirector}
              onConfirmBasis={setBasisTarget}
              onDestroy={setDestroyTarget}
            />
          )}
        </AsyncView>
      </section>

      {basisTarget && (
        <ConfirmDialog
          title="민감정보 확인"
          confirmLabel="확인했습니다"
          busy={basis.busy}
          error={basis.error}
          onConfirm={handleBasis}
          onCancel={closeBasis}
        >
          <p>
            <strong>{basisTarget.alias}</strong> 아동의 민감정보(건강 등) 처리에 대한 별도 동의 또는
            법령상 근거를 확인하셨나요? 확인하면 담당자 메모 원문을 입력할 수 있습니다.
          </p>
        </ConfirmDialog>
      )}

      {destroyTarget && (
        <ConfirmDialog
          title="아동 기록 파기"
          confirmLabel="파기"
          danger
          requireText={destroyTarget.alias}
          requireLabel="별칭 입력"
          requireHint="별칭이 정확히 같아야 파기할 수 있습니다."
          busy={destroy.busy}
          error={destroy.error}
          onConfirm={handleDestroy}
          onCancel={closeDestroy}
        >
          <p className="alert alert--error">
            <strong>{destroyTarget.alias}</strong>의 회차 기록·메모가 모두 삭제되고{' '}
            <strong>되돌릴 수 없습니다.</strong> 배정은 회수 처리되며, 감사 로그는 남습니다.
          </p>
          <p>
            확인을 위해 별칭 <strong>{destroyTarget.alias}</strong>
            {objectParticle(destroyTarget.alias)} 입력하세요.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}
