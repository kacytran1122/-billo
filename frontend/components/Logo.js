export default function Logo({ compact = false }) {
  return (
    <a className="logo" href="#top" aria-label="Billo home">
      <span className="logo-mark" aria-hidden="true">
        <span>@</span>
        <i>♥</i>
      </span>
      {!compact && <span className="logo-word">billo</span>}
    </a>
  );
}
