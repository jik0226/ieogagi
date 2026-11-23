import { useId } from 'react';

function useFieldIds(hint, error) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;
  return { id, hintId, errorId, describedBy };
}

function fieldClass(error) {
  return error ? 'field field--invalid' : 'field';
}

function FieldText({ hint, error, ids }) {
  return (
    <>
      {hint && (
        <p className="field__hint" id={ids.hintId}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field__error" id={ids.errorId} role="alert">
          {error}
        </p>
      )}
    </>
  );
}

export function TextField({ label, value, onChange, hint, error, type = 'text', ...inputProps }) {
  const ids = useFieldIds(hint, error);
  return (
    <div className={fieldClass(error)}>
      <label htmlFor={ids.id}>{label}</label>
      <input
        {...inputProps}
        id={ids.id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={ids.describedBy}
      />
      <FieldText hint={hint} error={error} ids={ids} />
    </div>
  );
}

export function TextAreaField({ label, value, onChange, hint, error, maxLength, ...areaProps }) {
  const ids = useFieldIds(hint, error);
  return (
    <div className={fieldClass(error)}>
      <div className="field__head">
        <label htmlFor={ids.id}>{label}</label>
        <span className="field__counter">
          {value.length}/{maxLength}
        </span>
      </div>
      <textarea
        {...areaProps}
        id={ids.id}
        value={value}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={ids.describedBy}
      />
      <FieldText hint={hint} error={error} ids={ids} />
    </div>
  );
}

export function SelectField({ label, value, onChange, options, placeholder, hint, error, ...selectProps }) {
  const ids = useFieldIds(hint, error);
  return (
    <div className={fieldClass(error)}>
      <label htmlFor={ids.id}>{label}</label>
      <select
        {...selectProps}
        id={ids.id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={ids.describedBy}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <FieldText hint={hint} error={error} ids={ids} />
    </div>
  );
}

export function CheckboxField({ label, checked, onChange, hint, error, ...inputProps }) {
  const ids = useFieldIds(hint, error);
  return (
    <div className={fieldClass(error)}>
      <label className="checkbox" htmlFor={ids.id}>
        <input
          {...inputProps}
          id={ids.id}
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          aria-describedby={ids.describedBy}
        />
        <span>{label}</span>
      </label>
      <FieldText hint={hint} error={error} ids={ids} />
    </div>
  );
}

export function RadioGroupField({ legend, value, onChange, options, hint, error }) {
  const ids = useFieldIds(hint, error);
  return (
    <fieldset className={fieldClass(error)} aria-describedby={ids.describedBy}>
      <legend>{legend}</legend>
      {options.map((option) => (
        <label key={option.value} className="radio">
          <input
            type="radio"
            name={ids.id}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span>{option.label}</span>
        </label>
      ))}
      <FieldText hint={hint} error={error} ids={ids} />
    </fieldset>
  );
}
