import { Chip } from "@/components/ui/Chip";
import { evidence } from "@/content/evidence.generated";
import { formatNumber } from "@/content/ledger";
import { guardMock } from "@/content/steps";
import { MockCard } from "../MockCard";
import styles from "./GuardCard.module.css";

const KEYWORD = /^(?:def|if|not|return|is|and|or|None|True|False)$/;
const SPLIT = /(\b(?:def|if|not|return|is|and|or|None|True|False)\b|'[^']*')/;

/** Split a line of Python into keywords, strings and plain runs, for light highlighting. */
function tokens(line: string) {
  return line.split(SPLIT).filter(Boolean);
}

/**
 * The saved model-generated guard, exactly as stored in examples/guards.
 * sync-evidence checks that this source hashes to the validated hash.
 */
export function GuardCard({ className }: { className?: string }) {
  const { guard, repair } = evidence;
  const lines = guard.source.split("\n");

  return (
    <MockCard className={className} title={guardMock.title} alt={guardMock.alt}>
      <div className={styles.chips}>
        <Chip mono>{repair.model.value}</Chip>
        <Chip mono>{guardMock.tokensLabel(formatNumber(repair.totalTokens.value))}</Chip>
        <Chip mono>{guardMock.attemptLabel(repair.attempts.value)}</Chip>
      </div>
      <pre className={styles.pre}>
        <code>
          {lines.map((line, index) => (
            <span key={index} className={styles.line}>
              <span className={styles.number}>{index + 1}</span>
              <span>
                {tokens(line).map((part, partIndex) =>
                  KEYWORD.test(part) ? (
                    <span key={partIndex} className={styles.keyword}>
                      {part}
                    </span>
                  ) : part.startsWith("'") ? (
                    <span key={partIndex} className={styles.string}>
                      {part}
                    </span>
                  ) : (
                    part
                  ),
                )}
              </span>
            </span>
          ))}
        </code>
      </pre>
      <div className={styles.foot}>
        <span>{guardMock.caption}</span>
        <code className={styles.hash}>
          {guardMock.hashLabel} {guard.shortHash}
        </code>
      </div>
    </MockCard>
  );
}
