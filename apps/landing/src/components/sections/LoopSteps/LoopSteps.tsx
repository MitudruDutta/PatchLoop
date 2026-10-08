import { ConversationCard } from "@/components/mocks/ConversationCard";
import { EffectCard } from "@/components/mocks/EffectCard";
import { GuardCard } from "@/components/mocks/GuardCard";
import { ValidationCard } from "@/components/mocks/ValidationCard";
import { LoopStepsView } from "./LoopStepsView";
import styles from "./LoopSteps.module.css";

/** The loop in three steps: find, repair, prove. Each step has a product mock beside it. */
export function LoopSteps() {
  return (
    <LoopStepsView
      visuals={[
        <div key="find" className={styles.stack}>
          <ConversationCard />
          <EffectCard />
        </div>,
        <GuardCard key="repair" />,
        <ValidationCard key="prove" />,
      ]}
    />
  );
}
