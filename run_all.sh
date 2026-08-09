#!/usr/bin/env bash
# Runs the configured public-provider examples, then scores their results.
# Comment out what you are not running. Safe to re-run: finished items skip.
set -euo pipefail

uv run python run_eval_litellm.py --model openai/gpt-5 \
  --tag gpt5 --max-tokens 256
uv run python run_eval_litellm.py --model anthropic/claude-opus-4-5 \
  --tag claude --max-tokens 256

# GPU, served with: vllm serve <model> --port 8000
# uv run python run_eval_litellm.py --model hosted_vllm/Qwen/Qwen3-8B \
#   --api-base http://localhost:8000/v1 --tag qwen3

# Local, quantized
# uv run python run_eval_litellm.py \
#   --model ollama/hf.co/linagora/Labess-7b-chat-gguf:Q4_K_M --tag labess

# For a corrected pass, add --items audit-sample-400-corrected.csv and use a
# distinct --tag ending in -corrected.

uv run python score.py
