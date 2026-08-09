#!/usr/bin/env bash
# Runs every model on the original sample, then scores.
# Comment out what you are not running. Safe to re-run: finished items skip.
set -u

python3 run_eval_litellm.py --model openai/gpt-5              --tag gpt5   --max-tokens 256
python3 run_eval_litellm.py --model anthropic/claude-opus-4-5 --tag claude --max-tokens 256

# GPU, served with: vllm serve <model> --port 8000
# python3 run_eval_litellm.py --model hosted_vllm/ESPRIT-Group/ESPRIT-Derja-Qwen3-8B-v2 --api-base http://localhost:8000/v1 --tag esprit
# python3 run_eval_litellm.py --model hosted_vllm/Qwen/Qwen3-8B                          --api-base http://localhost:8000/v1 --tag qwen3

# local, quantised
# python3 run_eval_litellm.py --model ollama/hf.co/linagora/Labess-7b-chat-gguf:Q4_K_M --tag labess

# second pass, once the corrected subset exists:
#   add  --items audit-sample-400-corrected.csv  and  --tag <name>-corrected

python3 score.py
