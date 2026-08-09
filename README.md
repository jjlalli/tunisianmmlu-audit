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

| model | original | corrected | delta |
|---|---|---|---|
| Gemini 3.1 Pro (n=400) | 89.2 | | |
| GPT-5.6 Sol (n=400) | 88.0 | | |
| Claude Sonnet 5 (n=400) | 79.2 | | |
| Qwen3-8B (4-bit, n=389) | 49.6 | 52.7 | +3.1 |
| ESPRIT-Derja-8B (4-bit, n=389) | 47.6 | 52.4 | +4.9 |
| Labess-7B (4-bit, n=389) | 29.6 | 29.8 | +0.3 |

Open models: same-389-item comparison, constrained answers, refusals 0.
