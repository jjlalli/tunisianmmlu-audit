#!/usr/bin/env bash
# Runs the configured public-provider examples, then scores their results.
# Comment out what you are not running. Safe to re-run: finished items skip.
set -euo pipefail

# The three commercial models of the paper (tags match the results-*.csv files).
# The identifiers are the ones evaluated; the transport depends on your provider:
# add --openai-compatible --api-base <url> --api-key-env <VAR> for an
# OpenAI-compatible gateway, or use the LiteLLM provider prefix directly.
uv run python run_eval_litellm.py --model openai/gpt-5.6-sol \
  --tag gpt-5.6-sol --max-tokens 256
uv run python run_eval_litellm.py --model anthropic/claude-sonnet-5 \
  --tag claude-sonnet-5 --max-tokens 256
uv run python run_eval_litellm.py --model google/gemini-3.1-pro-global \
  --tag gemini-3.1-pro --max-tokens 256

# GPU, served with: vllm serve <model> --port 8000
# uv run python run_eval_litellm.py --model hosted_vllm/Qwen/Qwen3-8B \
#   --api-base http://localhost:8000/v1 --tag qwen3

# Local, quantized
# uv run python run_eval_litellm.py \
#   --model ollama/hf.co/linagora/Labess-7b-chat-gguf:Q4_K_M --tag labess

# For a corrected pass, add --items audit-sample-400-corrected.csv and use a
# distinct --tag ending in -corrected.

uv run python score.py
