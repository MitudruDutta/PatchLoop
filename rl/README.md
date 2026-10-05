# RL workstream

**Owner:** Mitudru Dutta. **Requirements:** [docs/prd/rl-environment.md](../docs/prd/rl-environment.md).

This workstream builds a reinforcement-learning environment in which a model learns to write guards that pass PatchLoop's validation gates. It then measures whether RL improves on frozen and supervised models at matched budgets.

## Layout

| Path | Content |
|---|---|
| `src/patchloop/rl/` | The environment API: tasks, observations, actions and rewards. Standard library only, so it ships in the SDK. |
| `rl/configs/` | Training configurations with pinned framework commits (for example NeMo RL GRPO-LoRA) |
| `rl/scripts/` | Episode export, reward-parity checks, smoke runs and evaluation |
| `rl/data/` | Exported episodes. Ignored by git. |
| `rl/runs/` | Training outputs and checkpoints. Ignored by git. |

Create each directory when its first file exists. Keep GPU and training dependencies out of `src/patchloop/`.

## Rules

- Training rewards use training tasks and the training identity pool only. Sealed panels and held-out environments are for final evaluation.
- Generated code runs only through `patchloop.sandbox`.
- Record model, tokenizer, framework commit, seeds, hardware and cost for every run.
