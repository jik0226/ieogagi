// Status label. It always carries text, so meaning never depends on colour.
// `lock` adds a padlock for director-only features.
export default function Badge({ tone = 'neutral', lock = false, children }) {
  const classes = ['badge'];
  if (tone !== 'neutral') classes.push(`badge--${tone}`);
  if (lock) classes.push('badge--lock');
  return <span className={classes.join(' ')}>{children}</span>;
}
