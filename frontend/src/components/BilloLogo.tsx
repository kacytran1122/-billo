import type { CSSProperties } from "react";

type BilloLogoProps = {
  /** Rendered width and height in px. */
  size?: number;
  /** Stroke colour of the "b" mark. */
  stroke?: string;
  /** Fill of the coin/dot in the bowl. */
  dot?: string;
  style?: CSSProperties;
};

/** The Billo "b" mark: an open bowl with a coin inside. */
export function BilloLogo({
  size = 34,
  stroke = "var(--color-text)",
  dot = "var(--color-accent)",
  style,
}: BilloLogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{ flex: "none", ...style }} aria-hidden="true">
      <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke={stroke} strokeWidth="11" strokeLinecap="round" />
      <path
        d="M64 32 V56 Q64 68 75 68 Q86 68 86 50"
        fill="none"
        stroke={stroke}
        strokeWidth="11"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="47" cy="50" r="14" fill={dot} />
    </svg>
  );
}
