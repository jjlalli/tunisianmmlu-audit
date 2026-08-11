# TunisianMMLU audit — model evaluation

Private until camera-ready.

## Data

`audit-sample-400-master.csv` — 400 items stratified over all 44 subjects,
seed 20260805, from [linagora/TunisianMMLU](https://huggingface.co/datasets/linagora/TunisianMMLU).
CC BY-NC-SA 4.0, inherited.

`results-<tag>.csv` — one model's answers. `-corrected` suffix for the
second pass over corrected items.

## Run

Install [uv](https://docs.astral.sh/uv/), synchronize the locked environment,
and run the evaluator:

```bash
uv sync --locked
uv run python run_eval_litellm.py --model openai/gpt-5 --tag gpt5 --max-tokens 256
uv run python score.py
```

`./run_all.sh` runs the configured generic batch and then scores its results.
Completed items are skipped, so interrupted runs can be resumed.

`--items` swaps in the corrected subset. `ollama_chat/<model>` goes directly
to Ollama with a JSON-schema constrained answer; default runs use LiteLLM.
`--openai-compatible` selects the provider-neutral direct transport and
requires `--api-base` and `--api-key-env`; `--header` is repeatable.
By default, an unparsable response is recorded with `pred=-1`. Set
`--unparsed-retry-max-tokens` to retry once with a larger budget. For
`--openai-compatible` runs, `--unparsed-use-answer-tool` adds a constrained
answer-tool fallback after that retry.

| Model | Original dataset version, matched 389 | Corrected dataset version, 389 | Delta (percentage points) |
|---|---:|---:|---:|
| Gemini 3.1 Pro | 354/389 (91.0%) | 363/389 (93.3%) | +2.3 pp |
| GPT-5.6 Sol | 348/389 (89.5%) | 359/389 (92.3%) | +2.8 pp |
| Claude Sonnet 5 | 313/389 (80.5%) | 332/389 (85.3%) | +4.9 pp |
| Qwen3-8B (4-bit) | 193/389 (49.6%) | 205/389 (52.7%) | +3.1 pp |
| ESPRIT-Derja-8B (4-bit) | 185/389 (47.6%) | 204/389 (52.4%) | +4.9 pp |
| Labess-7B (4-bit) | 115/389 (29.6%) | 116/389 (29.8%) | +0.3 pp |

For a matched comparison, original predictions from `results-<tag>.csv` are
filtered to the 389 item IDs in `audit-sample-400-corrected.csv` before
scoring. Corrected scores come from `results-<tag>-corrected.csv`; 11 items
from the 400-item master set are excluded. Deltas use the unrounded count
fractions.

Exact model identifiers:

- Gemini 3.1 Pro — `google/gemini-3.1-pro-global`
- GPT-5.6 Sol — `openai/gpt-5.6-sol`
- Claude Sonnet 5 — `anthropic/claude-sonnet-5`
- Qwen3-8B — `Qwen/Qwen3-8B` (4-bit)
- ESPRIT-Derja-8B — `ESPRIT-Group/ESPRIT-Derja-Qwen3-8B-v2` (4-bit)
- Labess-7B — `linagora/Labess-7b-chat-gguf` (`Q4_K_M`)
