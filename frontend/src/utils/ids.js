const ID_PATTERN = /^[1-9][0-9]{0,9}$/;

// Route params arrive as strings; only plain positive integers are accepted.
export function isNumericId(value) {
  return typeof value === 'string' && ID_PATTERN.test(value);
}
