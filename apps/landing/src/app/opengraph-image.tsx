import { ImageResponse } from "next/og";
import { hero } from "@/content/hero";
import { metadataCopy, siteName } from "@/content/site";

export const alt = metadataCopy.ogAlt;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Brand colours from packages/brand/tokens.css. ImageResponse cannot read CSS variables.
const FIELD = "#12281c";
const CREAM = "#f1f5ea";
const SIGNAL = "#d6f272";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          width: "100%",
          height: "100%",
          padding: 72,
          background: FIELD,
          color: CREAM,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 34, fontWeight: 600 }}>
          <svg width="52" height="52" viewBox="0 0 28 28" fill="none">
            <rect x="0.75" y="0.75" width="26.5" height="26.5" rx="7.25" stroke={CREAM} strokeWidth="1.5" />
            <g transform="translate(14 14) scale(0.6) translate(-12 -12)">
              <path
                d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"
                stroke={SIGNAL}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path d="M21 3v5h-5" stroke={SIGNAL} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </g>
          </svg>
          {siteName}
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: 30, color: SIGNAL }}>{hero.eyebrow}</div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              marginTop: 22,
              fontSize: 104,
              lineHeight: 1.06,
              letterSpacing: -3.6,
            }}
          >
            <span>{hero.headline[0]}</span>
            <span>{hero.headline[1]}</span>
          </div>
        </div>
      </div>
    ),
    size,
  );
}
