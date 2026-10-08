import { stages } from "@/content/stages";
import { cn } from "@/lib/cn";
import styles from "./CallField.module.css";

// Geometry in viewBox units (640 x 620).
type Point = [number, number];

const AGENT = { x: 28, y: 262, width: 124, height: 96 };
const RECORD = { x: 470, width: 150, height: 60 };
const START: Point = [AGENT.x + AGENT.width, AGENT.y + AGENT.height / 2];
const BOUNDARY_X = 352;
const LEDGER = { x: 28, y: 556, width: 592, height: 48 };

const records = [
  { y: 58, owned: true },
  { y: 138, owned: true },
  { y: 218, owned: true },
  { y: 372, owned: false },
  { y: 452, owned: false },
];

const lerp = (a: Point, b: Point, t: number): Point => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];

/** Split a cubic curve at `t` into the part before and the part after. */
function split(curve: Point[], t: number) {
  const [p0, p1, p2, p3] = curve;
  const a = lerp(p0, p1, t);
  const b = lerp(p1, p2, t);
  const c = lerp(p2, p3, t);
  const d = lerp(a, b, t);
  const e = lerp(b, c, t);
  const f = lerp(d, e, t);
  return { head: [p0, a, d, f], tail: [f, e, c, p3] };
}

/** The `t` at which a left-to-right curve crosses the vertical line at `x`. */
function tAtX(curve: Point[], x: number) {
  let low = 0;
  let high = 1;
  for (let step = 0; step < 24; step += 1) {
    const mid = (low + high) / 2;
    if (split(curve, mid).head[3][0] < x) low = mid;
    else high = mid;
  }
  return (low + high) / 2;
}

const fmt = (point: Point) => `${point[0].toFixed(1)} ${point[1].toFixed(1)}`;
const toPath = (curve: Point[]) => `M${fmt(curve[0])}C${fmt(curve[1])} ${fmt(curve[2])} ${fmt(curve[3])}`;

const calls = records.map((record, index) => {
  const end: Point = [RECORD.x, record.y + RECORD.height / 2];
  const curve: Point[] = [START, [300, START[1]], [320, end[1]], end];
  const { head, tail } = split(curve, tAtX(curve, BOUNDARY_X));
  return {
    ...record,
    full: toPath(curve),
    toBoundary: toPath(head),
    pastBoundary: toPath(tail),
    stop: head[3],
    // Stagger the travelling calls so they never move in step.
    duration: 2.6 + index * 0.35,
    delay: index * 0.55,
  };
});

// Marks in the ledger strip. They are tallies, not counts from a run.
const LEDGER_MARKS = [true, true, false, true, true, true, false, true, true, false, true, true];

type Props = {
  /** 0: rules in the prompt. 1: rules at the tool boundary. 2: rules with evidence. */
  stage: 0 | 1 | 2;
  className?: string;
};

/**
 * Calls travelling from the agent to five records, three owned by the session
 * user and two by other customers. The drawing is complete without motion:
 * the travelling dots only repeat what the lines and labels already show.
 */
export function CallField({ stage, className }: Props) {
  const guarded = stage > 0;
  const { art } = stages;

  return (
    <svg className={cn(styles.field, className)} viewBox="0 0 640 620" fill="none" aria-hidden focusable="false">
      {/* Group labels */}
      <text className={styles.groupLabel} x={RECORD.x} y={records[0].y - 14}>
        {art.session}
      </text>
      <text className={styles.groupLabel} x={RECORD.x} y={records[3].y - 14}>
        {art.others}
      </text>

      {/* Call paths */}
      {calls.map((call) => {
        const blocked = guarded && !call.owned;
        return (
          <g key={call.y}>
            {blocked ? (
              <>
                <path className={styles.path} d={call.toBoundary} />
                <path className={styles.pathCut} d={call.pastBoundary} />
              </>
            ) : (
              <path className={cn(styles.path, !guarded && !call.owned && styles.pathUnsafe)} d={call.full} />
            )}
          </g>
        );
      })}

      {/* The guard's boundary */}
      {guarded && (
        <g>
          <line className={styles.boundary} x1={BOUNDARY_X} y1="34" x2={BOUNDARY_X} y2="536" />
          <rect className={styles.boundaryTag} x={BOUNDARY_X - 31} y="12" width="62" height="24" rx="6" />
          <text className={styles.boundaryText} x={BOUNDARY_X} y="28" textAnchor="middle">
            {art.boundary}
          </text>
          {calls
            .filter((call) => !call.owned)
            .map((call) => (
              <g key={call.y} transform={`translate(${call.stop[0].toFixed(1)} ${call.stop[1].toFixed(1)})`}>
                <circle className={styles.stopDisc} r="9" />
                <path className={styles.stopSlash} d="M-4.5 4.5L4.5 -4.5" />
              </g>
            ))}
        </g>
      )}

      {/* Travelling calls */}
      <g className={styles.motion}>
        {calls.map((call) => {
          const blocked = guarded && !call.owned;
          return (
            <circle key={call.y} className={cn(styles.dot, blocked && styles.dotBlocked)} r="4">
              <animateMotion
                dur={`${call.duration}s`}
                begin={`${call.delay}s`}
                repeatCount="indefinite"
                path={blocked ? call.toBoundary : call.full}
              />
              <animate
                attributeName="opacity"
                values="0;1;1;0"
                keyTimes="0;0.12;0.86;1"
                dur={`${call.duration}s`}
                begin={`${call.delay}s`}
                repeatCount="indefinite"
              />
            </circle>
          );
        })}
      </g>

      {/* Agent */}
      <rect className={styles.agent} x={AGENT.x} y={AGENT.y} width={AGENT.width} height={AGENT.height} rx="14" />
      <circle className={styles.agentDot} cx={AGENT.x + AGENT.width / 2} cy={AGENT.y + 36} r="9" />
      <text className={styles.agentLabel} x={AGENT.x + AGENT.width / 2} y={AGENT.y + 70} textAnchor="middle">
        {art.agent}
      </text>

      {/* Records */}
      {calls.map((call) => {
        const changed = !guarded && !call.owned;
        const word = call.owned ? null : changed ? art.changed : art.untouched;
        const pillWidth = word ? word.length * 6.6 + 18 : 0;
        return (
          <g key={call.y}>
            <rect
              className={cn(styles.record, changed && styles.recordChanged)}
              x={RECORD.x}
              y={call.y}
              width={RECORD.width}
              height={RECORD.height}
              rx="10"
            />
            <rect className={styles.bar} x={RECORD.x + 14} y={call.y + 19} width="46" height="6" rx="3" />
            <rect className={styles.barSoft} x={RECORD.x + 14} y={call.y + 34} width="30" height="6" rx="3" />
            {word ? (
              <>
                <rect
                  className={cn(styles.pill, changed && styles.pillChanged)}
                  x={RECORD.x + RECORD.width - pillWidth - 10}
                  y={call.y + 19}
                  width={pillWidth}
                  height="22"
                  rx="5"
                />
                <text
                  className={cn(styles.pillText, changed && styles.pillTextChanged)}
                  x={RECORD.x + RECORD.width - pillWidth / 2 - 10}
                  y={call.y + 34}
                  textAnchor="middle"
                >
                  {word}
                </text>
              </>
            ) : (
              <path
                className={styles.check}
                d={`M${RECORD.x + RECORD.width - 30} ${call.y + 30}l5 5 9-10`}
              />
            )}
          </g>
        );
      })}

      {/* Ledger */}
      {stage === 2 && (
        <g>
          <rect
            className={styles.ledger}
            x={LEDGER.x}
            y={LEDGER.y}
            width={LEDGER.width}
            height={LEDGER.height}
            rx="10"
          />
          <text className={styles.ledgerLabel} x={LEDGER.x + 18} y={LEDGER.y + 29}>
            {art.ledger}
          </text>
          {LEDGER_MARKS.map((preserved, index) => (
            <rect
              key={index}
              className={preserved ? styles.markPreserved : styles.markBlocked}
              x={LEDGER.x + 96 + index * 17}
              y={LEDGER.y + 16}
              width="10"
              height="16"
              rx="3"
            />
          ))}
          <rect className={styles.markPreserved} x={LEDGER.x + 340} y={LEDGER.y + 19} width="10" height="10" rx="3" />
          <text className={styles.legend} x={LEDGER.x + 357} y={LEDGER.y + 28}>
            {art.preserved}
          </text>
          <rect className={styles.markBlocked} x={LEDGER.x + 460} y={LEDGER.y + 19} width="10" height="10" rx="3" />
          <text className={styles.legend} x={LEDGER.x + 477} y={LEDGER.y + 28}>
            {art.blocked}
          </text>
        </g>
      )}
    </svg>
  );
}
