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
Unparsable responses retry once with a larger completion budget and then use
a constrained answer tool rather than writing an invalid result.

| | original |
|---|---|
| labess (Q4_K_M) | 29.0% |
