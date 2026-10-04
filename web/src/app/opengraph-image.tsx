import { ImageResponse } from "next/og";

// output: "export" requires route handlers to opt into static generation.
export const dynamic = "force-static";

// OG image (round 178): a branded social-sharing card for the root/dashboard.
// Rendered at build time (SSG-safe for output: 'export') — 1200×630 standard.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "Aionis — 反泄漏选股研究终端";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #0a0a0a 0%, #111 100%)",
          color: "#ededed",
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 20,
            marginBottom: 24,
          }}
        >
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: 16,
              background: "#00ca50",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 42,
              fontWeight: 700,
              color: "#0a0a0a",
            }}
          >
            A
          </div>
          <div style={{ fontSize: 56, fontWeight: 700, letterSpacing: -1 }}>
            Aionis
          </div>
        </div>
        <div style={{ fontSize: 28, color: "#a3a3a3", marginTop: 8 }}>
          反泄漏选股研究终端 · Anti-leakage stock-pick research terminal
        </div>
        <div
          style={{
            display: "flex",
            gap: 32,
            marginTop: 40,
            fontSize: 20,
            color: "#00ca50",
          }}
        >
          <span>● PIT data</span>
          <span>● Frozen configs</span>
          <span>● 4 NULL verdicts</span>
          <span>● H6 deterministic</span>
        </div>
      </div>
    ),
    size,
  );
}
