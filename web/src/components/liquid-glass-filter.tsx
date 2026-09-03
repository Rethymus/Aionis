// LiquidGlassFilter — the Chrome-path lensing filter for the nav dropdown.
//
// Per the Liquid Glass research (reports/design/2026-09-03-apple-motion-research.md,
// citing WWDC25-219 + kube.io): the glass "lensing" effect is a per-pixel
// displacement of the backdrop, strongest at the panel edges, encoded as an
// R=X / G=Y displacement map (128 = neutral) and applied with
// feDisplacementMap. Blur + saturation ride the same filter chain. The map
// (web/public/liquid-glass-map.png, generated with an 18% edge band and a
// 1.6-power falloff) is referenced by feImage.
//
// Applied via `backdrop-filter: url(#liquid-glass-lens)` — Chrome/Edge only;
// Firefox does not run SVG filters inside backdrop-filter, and every other
// browser keeps the plain blur()/saturate() declaration in globals.css.
// `scale` on the displacement is the animatable knob (Apple's "modulating
// lensing"): reduce it and the glass melts into plain blur.

export function LiquidGlassFilter() {
  return (
    <svg
      width="0"
      height="0"
      aria-hidden="true"
      style={{ position: "absolute" }}
    >
      <filter
        id="liquid-glass-lens"
        x="0"
        y="0"
        width="100%"
        height="100%"
        colorInterpolationFilters="sRGB"
      >
        <feImage
          href="/liquid-glass-map.png"
          x="0"
          y="0"
          width="100%"
          height="100%"
          preserveAspectRatio="none"
          result="map"
        />
        <feDisplacementMap
          in="SourceGraphic"
          in2="map"
          scale={18}
          xChannelSelector="R"
          yChannelSelector="G"
          result="displaced"
        />
        <feGaussianBlur in="displaced" stdDeviation="7" result="blurred" />
        <feColorMatrix in="blurred" type="saturate" values="1.8" />
      </filter>
    </svg>
  );
}
