import { useState } from 'react';

export default function CopyButton({ text, label = '복사', onCopied }) {
  const [status, setStatus] = useState('idle');

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setStatus('done');
      onCopied?.();
    } catch {
      setStatus('failed');
    }
  }

  return (
    <>
      <button type="button" className="btn btn--small" onClick={copy}>
        {status === 'done' ? '복사했습니다' : label}
      </button>
      <span className="visually-hidden" role="status">
        {status === 'done' ? '복사했습니다' : ''}
      </span>
      {status === 'failed' && (
        <span className="field__error" role="alert">
          복사하지 못했습니다. 직접 선택해서 복사해 주세요.
        </span>
      )}
    </>
  );
}
