import { StatusBadge } from "@/components/ui/StatusBadge";
import { illustrativeTag } from "@/content/site";
import { conversationMock } from "@/content/steps";
import { MockCard } from "../MockCard";
import styles from "./ConversationCard.module.css";

/** A tester's request, the tool call the agent made, and the agent's reply. */
export function ConversationCard({ className }: { className?: string }) {
  const { title, tester, agent, call, alt } = conversationMock;
  return (
    <MockCard
      className={className}
      title={title}
      alt={alt}
      aside={<StatusBadge kind="illustrative">{illustrativeTag}</StatusBadge>}
    >
      <div className={styles.turn}>
        <span className="t-label">{tester.speaker}</span>
        <p className={styles.bubble}>{tester.text}</p>
      </div>
      <div className={styles.call}>
        <span className="t-label">{call.label}</span>
        <code className={styles.code}>
          <span className={styles.name}>{call.name}</span>({call.args})
        </code>
      </div>
      <div className={styles.turn}>
        <span className="t-label">{agent.speaker}</span>
        <p className={styles.bubble}>{agent.text}</p>
      </div>
    </MockCard>
  );
}
