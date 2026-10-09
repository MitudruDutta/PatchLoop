#!/bin/bash
# Three tester runs against the loose rules (can it find the leaks?) and three against the proper rules (false alarms?).
set -u
for rules in loose proper; do
  file=rules.json; [ "$rules" = loose ] && file=rules.loose.json
  for n in 1 2 3; do
    rm -f calls.jsonl
    PATCHLOOP_RULES=$file PATCHLOOP_MODE=enforce patchloop test wallet_agent --scenarios 5 --turns 2 \
      --max-requests 25 --report tester-runs/$rules-$n.json 2>/dev/null | tail -1
  done
done
