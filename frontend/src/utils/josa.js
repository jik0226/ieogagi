const HANGUL_START = 0xac00;
const HANGUL_END = 0xd7a3;

// Picks 을/를 for a word by its last Korean syllable. Anything that does not
// end in Hangul gets the neutral "을(를)".
export function objectParticle(word) {
  const text = String(word ?? '');
  const code = text.length > 0 ? text.charCodeAt(text.length - 1) : 0;
  if (code < HANGUL_START || code > HANGUL_END) return '을(를)';
  return (code - HANGUL_START) % 28 === 0 ? '를' : '을';
}
