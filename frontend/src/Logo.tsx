type LogoProps = {
  height?: number;
  /** "dark" (default) = ink text for light backgrounds, matching Landing/
   * Login/Signup. "light" = paper/amber text for dark backgrounds, e.g.
   * the AppShell sidebar — the default dark-ink wordmark wouldn't read
   * against that background. */
  variant?: "dark" | "light";
};

/** Inlined (not an <img src>) so the Fraunces web font — only loaded on the
 * host page via the Google Fonts <link> in index.html — actually applies.
 * An external SVG <img> renders in an isolated context without access to
 * that font and falls back to a generic serif.
 *
 * viewBox is 270 wide, not the original asset's 220 — measured directly
 * (text.getBBox()) with Fraunces actually loaded, "healthcare.agent" at
 * font-size 24 starting at x=66 runs to x≈256, so the original 220 clipped
 * the last few letters ("...agen|t") — a bug in the source asset, not a
 * scaling issue. Only the viewBox changed; icon/text coordinates are untouched. */
export function Logo({ height = 32, variant = "dark" }: LogoProps) {
  const width = (270 / 56) * height;
  const textColor = variant === "light" ? "#F1F3EE" : "#16231F";
  const accentColor = variant === "light" ? "#D9A441" : "#2F6F62";
  return (
    <svg width={width} height={height} viewBox="0 0 270 56" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="healthcare.agent">
      <g transform="translate(4,4)">
        <rect x="0" y="0" width="48" height="48" rx="14" fill="#2F6F62" />
        <path
          d="M10 15 C10 11.7 12.7 9 16 9 L32 9 C35.3 9 38 11.7 38 15 L38 27 C38 30.3 35.3 33 32 33 L20 33 L13 39 L13 33 C11.3 32.7 10 31.2 10 29 Z"
          fill="none"
          stroke="#F1F3EE"
          strokeWidth={2.4}
          strokeLinejoin="round"
        />
        <path
          d="M14 21 L19 21 L22 15 L26 27 L29 21 L34 21"
          fill="none"
          stroke="#D9A441"
          strokeWidth={2.6}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
      <text x="66" y="34" fontFamily="Fraunces, serif" fontSize={24} fontWeight={500} fill={textColor}>
        healthcare<tspan fill={accentColor}>.agent</tspan>
      </text>
    </svg>
  );
}
