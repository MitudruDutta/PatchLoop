import type { CSSProperties } from "react";
import { hero } from "@/content/hero";
import { cn } from "@/lib/cn";
import styles from "./LoopField.module.css";

// Geometry in viewBox units. The orbits are one ring seen at a low angle:
// the lower arc is the near side, the upper arc runs behind the hero copy.
const CENTRE_X = 720;
const CENTRE_Y = 520;
// The loop itself, then its echoes: each wider and fainter than the last.
const ORBITS = [
  { rx: 600, ry: 130, opacity: 1 },
  { rx: 780, ry: 169, opacity: 0.78 },
  { rx: 980, ry: 212, opacity: 0.58 },
  { rx: 1200, ry: 260, opacity: 0.42 },
];
const TRACK = ORBITS[0];
const SEGMENTS = 240;
/** Seconds for the call to travel the loop once. */
const PERIOD = 14;
/** Share of the period spent on the near arc. The far arc is the return trip, so it is quicker. */
const NEAR_SHARE = 0.7;
/** Station positions on the near arc, left to right, in degrees. */
const STATION_ANGLES = [150, 120, 90, 60, 30];
const VALIDATE_INDEX = 3;
/** The call's wake: share of the loop each layer covers, longest and faintest first. */
const WAKE = [
  { share: 0.07, opacity: 0.1 },
  { share: 0.036, opacity: 0.22 },
  { share: 0.014, opacity: 0.5 },
];

function pointAt(angle: number) {
  const radians = (angle * Math.PI) / 180;
  return { x: CENTRE_X + TRACK.rx * Math.cos(radians), y: CENTRE_Y + TRACK.ry * Math.sin(radians) };
}

// The call's path: from the far left, along the near arc to the right, and back behind.
// It is a polyline so that its length here matches the browser's, which keeps the
// stations in step with the travelling dot.
const trackPoints = Array.from({ length: SEGMENTS + 1 }, (_, index) => pointAt(180 - (360 * index) / SEGMENTS));
const trackPath = `${trackPoints
  .map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
  .join("")}Z`;

const lengths = [0];
for (let index = 1; index < trackPoints.length; index += 1) {
  const a = trackPoints[index - 1];
  const b = trackPoints[index];
  lengths.push(lengths[index - 1] + Math.hypot(b.x - a.x, b.y - a.y));
}
const trackLength = lengths[lengths.length - 1];

/** Share of the loop travelled when the call reaches `angle` on the near arc. */
function progressAt(angle: number) {
  return lengths[Math.round(((180 - angle) / 360) * SEGMENTS)] / trackLength;
}

/** Seconds into the period when the call reaches `angle` on the near arc. */
function arrivalAt(angle: number) {
  return (progressAt(angle) / 0.5) * NEAR_SHARE * PERIOD;
}

const stations = STATION_ANGLES.map((angle, index) => ({
  ...pointAt(angle),
  label: hero.stations[index],
  arrival: arrivalAt(angle).toFixed(2),
}));

// Shared by the dot and its wake, so they keep the same pace round the loop.
const pace = {
  dur: `${PERIOD}s`,
  keyTimes: `0;${NEAR_SHARE};1`,
  calcMode: "linear",
  repeatCount: "indefinite",
} as const;

type Props = {
  /** Unique per instance: the SVG's gradient ids are built from it. */
  id: string;
  /** Orbits only: no stations and no travelling call. */
  quiet?: boolean;
  className?: string;
};

/**
 * The hero illustration: concentric orbits with the five stations of the loop
 * and one call travelling round it. Decorative; the page copy carries the meaning.
 */
export function LoopField({ id, quiet = false, className }: Props) {
  const stroke = `${id}-stroke`;
  const glow = `${id}-glow`;

  return (
    <svg
      className={cn(styles.field, className)}
      viewBox="0 280 1440 620"
      fill="none"
      aria-hidden
      focusable="false"
      style={{ "--period": `${PERIOD}s` } as CSSProperties}
    >
      <defs>
        <linearGradient id={stroke} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--cream)" stopOpacity="0.05" />
          <stop offset="0.55" stopColor="var(--cream)" stopOpacity="0.14" />
          <stop offset="1" stopColor="var(--cream)" stopOpacity="0.34" />
        </linearGradient>
        <radialGradient id={glow}>
          <stop offset="0" stopColor="var(--signal)" stopOpacity="0.5" />
          <stop offset="0.4" stopColor="var(--signal)" stopOpacity="0.14" />
          <stop offset="1" stopColor="var(--signal)" stopOpacity="0" />
        </radialGradient>
      </defs>

      {ORBITS.map((orbit) => (
        <ellipse
          key={orbit.rx}
          cx={CENTRE_X}
          cy={CENTRE_Y}
          rx={orbit.rx}
          ry={orbit.ry}
          stroke={`url(#${stroke})`}
          strokeWidth={orbit === TRACK ? 1.25 : 1}
          opacity={orbit.opacity}
          vectorEffect="non-scaling-stroke"
        />
      ))}

      {!quiet && (
        <>
          <g className={styles.call}>
            {WAKE.map((layer) => {
              const share = layer.share * 100;
              return (
                <path
                  key={layer.share}
                  className={styles.wake}
                  d={trackPath}
                  pathLength={100}
                  strokeDasharray={`${share} ${100 - share}`}
                  opacity={layer.opacity}
                >
                  {/* Keeps the leading end of the dash on the dot. */}
                  <animate attributeName="stroke-dashoffset" values={`${share};${share - 50};${share - 100}`} {...pace} />
                </path>
              );
            })}
          </g>

          <g className={styles.stations}>
            {stations.map((station, index) => (
              <g key={station.label} style={{ "--arrival": `${station.arrival}s` } as CSSProperties}>
                {index === VALIDATE_INDEX && <circle className={styles.pulse} cx={station.x} cy={station.y} r="5" />}
                <circle className={styles.stationDot} cx={station.x} cy={station.y} r="4.5" />
                <text className={styles.stationLabel} x={station.x} y={station.y + 28} textAnchor="middle">
                  {station.label}
                </text>
              </g>
            ))}
          </g>

          <g className={styles.call}>
            <circle r="22" fill={`url(#${glow})`} />
            <circle r="3.5" fill="var(--signal)" />
            <animateMotion path={trackPath} keyPoints="0;0.5;1" {...pace} />
          </g>
          {/* Shown in place of the travelling call when motion is reduced. */}
          <g className={styles.callStill} transform={`translate(${stations[0].x} ${stations[0].y})`}>
            <circle r="22" fill={`url(#${glow})`} />
            <circle r="3.5" fill="var(--signal)" />
          </g>
        </>
      )}
    </svg>
  );
}
