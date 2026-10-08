import { BuiltOn } from "@/components/sections/BuiltOn";
import { Closer } from "@/components/sections/Closer";
import { EffectsLedger } from "@/components/sections/EffectsLedger";
import { Faq } from "@/components/sections/Faq";
import { Hero } from "@/components/sections/Hero";
import { LoopSteps } from "@/components/sections/LoopSteps";
import { Pricing } from "@/components/sections/Pricing";
import { RuleFlow } from "@/components/sections/RuleFlow";
import { RuleStages } from "@/components/sections/RuleStages";
import { TrustTiles } from "@/components/sections/TrustTiles";
import { LeadDialogProvider } from "@/components/ui/LeadDialog";

// Sections in the order of docs/prd/landing.md, section 7. The nav is part of the hero.
export default function Home() {
  return (
    <LeadDialogProvider>
      <main id="main-content">
        <Hero />
        <RuleStages />
        <LoopSteps />
        <EffectsLedger />
        <RuleFlow />
        <TrustTiles />
        <Pricing />
        <Faq />
        <BuiltOn />
      </main>
      <Closer />
    </LeadDialogProvider>
  );
}
