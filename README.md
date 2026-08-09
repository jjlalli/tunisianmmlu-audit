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

| | original |
|---|---|
| Gemini 3.1 Pro Global | 89.2% |
| GPT-5.6 Sol | 88.0% |
| Claude Sonnet 5 | 79.2% |
| labess (Q4_K_M) | 29.0% |
