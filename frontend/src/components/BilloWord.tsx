/**
 * Inline "billo" wordmark used inside chat bubbles and headlines.
 * Inherits font size and colour from its parent; only the coin is coloured.
 */
export function BilloWord({ dot = "oklch(0.84 0.16 92)" }: { dot?: string }) {
  return (
    <span
      aria-label="billo"
      style={{
        display: "inline-flex",
        alignItems: "baseline",
        gap: ".06em",
        whiteSpace: "nowrap",
        fontStyle: "normal",
        fontWeight: 400,
        verticalAlign: "baseline",
      }}
    >
      <svg viewBox="0 0 100 100" style={{ width: "1em", height: "1em", alignSelf: "center", flex: "none" }} aria-hidden="true">
        <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="currentColor" strokeWidth="11" strokeLinecap="round" />
        <path
          d="M64 32 V56 Q64 68 75 68 Q86 68 86 50"
          fill="none"
          stroke="currentColor"
          strokeWidth="11"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="47" cy="50" r="14" fill={dot} />
      </svg>
      billo
    </span>
  );
}
