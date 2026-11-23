import { recordFieldEntries } from '../utils/labels.js';

// The three record fields (did / stuck / next_step) as a definition list.
// Text is rendered as plain text; React escapes it.
// - `emphasize`: name of the field to stand out (the "next step" on the
//   hand-over card).
// - `hideEmpty`: leave out fields nobody filled in.
// - `past`: label the fields for an earlier session ("그날 한 것"). Every
//   shown record is one, so it defaults to true; only the input form says
//   "오늘 한 것".
export default function RecordFields({ record, emphasize, hideEmpty = false, past = true }) {
  const entries = recordFieldEntries(record, { past }).filter(
    (field) => !hideEmpty || field.value !== '',
  );

  if (entries.length === 0) {
    return <p className="meta">(내용이 비어 있습니다)</p>;
  }

  return (
    <dl className="record__fields">
      {entries.map((field) => (
        <div key={field.name} className={field.name === emphasize ? 'record__field--emphasis' : undefined}>
          <dt>{field.label}</dt>
          <dd className={field.value ? undefined : 'record__empty'}>{field.value || '(비어 있음)'}</dd>
        </div>
      ))}
    </dl>
  );
}
