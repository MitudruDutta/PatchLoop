export const faq = {
  heading: "Questions you might have",
  items: [
    {
      question: "How is PatchLoop different from red-teaming tools and guardrails?",
      answer:
        "Red-teaming tools find problems and stop. Guardrails block calls with rules that people write. PatchLoop closes the loop: it finds the violation, generates the guard, and shows the evidence that the fix holds and legitimate work still passes.",
    },
    {
      question: "Why not write the authorization checks by hand?",
      answer:
        "For a small, fixed application that may be the best answer, and we keep a handwritten guard as a comparison. PatchLoop is for finding the gap you did not know about and for proving a fix without breaking what works.",
    },
    {
      question: "Does a passing guard mean my agent is secure?",
      answer:
        "No. It means a specific failure is contained and specific checks passed on named cases. That is evidence you can rerun, not a proof that no failure remains.",
    },
    {
      question: "What do I need to connect my own agent?",
      answer:
        "Your tools, a way to run them against a test environment, the session's identity from your own authentication, your policy in plain text, and recorded legitimate calls. There is no one-line integration. The generic connector is still being built; today PatchLoop ships with the τ-bench retail agent.",
    },
    {
      question: "Does my code or data leave my environment?",
      answer:
        "The runner executes your tools and the generated guards on your own machine. Model calls go to the provider you configure, with your key.",
    },
    {
      question: "Which models does it use?",
      answer:
        "NVIDIA Nemotron through Nebius Token Factory for the agent, the tester and the repair worker, and Tavily for public reference guidance. You bring your own keys.",
    },
    {
      question: "What does PatchLoop not check?",
      answer:
        "Answer quality, facts and tone. Concurrency and duplicate operations. Business rules that are not written into a contract.",
    },
    {
      question: "Is it ready for production?",
      answer:
        "Not yet. It is a local product on one synthetic benchmark. Public hosting, a measured comparison study and the generic connector are still to come.",
    },
  ],
} as const;
