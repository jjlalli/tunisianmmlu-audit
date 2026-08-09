# TunisianMMLU audit — model evaluation

Private until camera-ready.

## Data

`audit-sample-400-master.csv` — 400 items stratified over all 44 subjects,
seed 20260805, from [linagora/TunisianMMLU](https://huggingface.co/datasets/linagora/TunisianMMLU).
CC BY-NC-SA 4.0, inherited.

`results-<tag>.csv` — one model's answers. `-corrected` suffix for the
second pass over corrected items.

## Run

```
pip install litellm
python3 run_eval_litellm.py --model openai/gpt-5 --tag gpt5 --max-tokens 256
python3 score.py
```

`--items` swaps in the corrected subset. `ollama_chat/<model>` goes direct
to Ollama with a JSON-schema constrained answer; everything else routes
through LiteLLM.

| | original |
|---|---|
| labess (Q4_K_M) | 29.0% |
