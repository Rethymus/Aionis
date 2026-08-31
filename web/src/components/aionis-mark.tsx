// The Aionis brand mark, inline (no image request, no basePath concerns):
// the letter A whose counter holds a monthly rank-IC series inside confidence
// bounds around a zero axis — the project's null-result headline, drawn.
// Same art as assets/aionis-logo.svg and web/src/app/icon.svg (favicon).
export function AionisMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 512 512"
      role="img"
      aria-label="Aionis"
      className={className}
    >
      <defs>
        <linearGradient id="aionis-mark-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0B1220" />
          <stop offset="1" stopColor="#1A2C4C" />
        </linearGradient>
        <linearGradient id="aionis-mark-ic" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#2DD4BF" />
          <stop offset="1" stopColor="#F59E0B" />
        </linearGradient>
      </defs>
      <rect x="16" y="16" width="480" height="480" rx="100" fill="url(#aionis-mark-bg)" />
      <rect
        x="21"
        y="21"
        width="470"
        height="470"
        rx="95"
        fill="none"
        stroke="#2E4165"
        strokeWidth="4"
        opacity="0.9"
      />
      <line x1="154" y1="390" x2="256" y2="128" stroke="#E7EEF9" strokeWidth="28" strokeLinecap="round" />
      <line x1="256" y1="128" x2="358" y2="390" stroke="#E7EEF9" strokeWidth="28" strokeLinecap="round" />
      <line x1="224" y1="272" x2="288" y2="272" stroke="#43597F" strokeWidth="5" strokeLinecap="round" strokeDasharray="12 14" />
      <line x1="224" y1="320" x2="288" y2="320" stroke="#43597F" strokeWidth="5" strokeLinecap="round" strokeDasharray="12 14" />
      <line x1="214" y1="296" x2="294" y2="296" stroke="#8FA3C4" strokeWidth="6" strokeLinecap="round" strokeDasharray="1 16" />
      <polyline
        points="216,296 234,285 252,303 270,279 290,291"
        fill="none"
        stroke="url(#aionis-mark-ic)"
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="216" cy="296" r="6.5" fill="#2DD4BF" />
      <circle cx="234" cy="285" r="6.5" fill="#2DD4BF" />
      <circle cx="252" cy="303" r="6.5" fill="#35BFAE" />
      <circle cx="270" cy="279" r="6.5" fill="#7FA671" />
      <circle cx="290" cy="291" r="7.5" fill="#F59E0B" />
    </svg>
  );
}
