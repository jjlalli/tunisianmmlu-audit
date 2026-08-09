#!/usr/bin/env python3
"""Evaluate one model on the TunisianMMLU audit sample via LiteLLM.

    export OPENAI_API_KEY=...        # for openai/*
    export ANTHROPIC_API_KEY=...     # for anthropic/*
    export GEMINI_API_KEY=...        # for gemini/*

Examples
    uv run python run_eval_litellm.py --model openai/gpt-5              --tag gpt5
    uv run python run_eval_litellm.py --model anthropic/claude-opus-4-5 --tag claude
    uv run python run_eval_litellm.py --model ollama/hf.co/linagora/Labess-7b-chat-gguf:Q4_K_M --tag labess
    uv run python run_eval_litellm.py --model hosted_vllm/Qwen/Qwen3-8B --api-base http://localhost:8000/v1 --tag qwen3
    uv run python run_eval_litellm.py --model hosted_vllm/ESPRIT-Group/ESPRIT-Derja-Qwen3-8B-v2 --api-base http://localhost:8000/v1 --tag esprit

Re-run the same command after an interruption: completed items are skipped.
Use --items to point at the corrected subset for the second pass.

Output: results-<tag>.csv with item_id, subject, source, gold, pred,
correct, raw. `pred = -1` means the model returned no parsable digit; those
are counted incorrect and the refusal rate is reported separately.
"""

import argparse
import csv
import os
import re
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))

PROMPT = (
    "جاوب على السؤال التالي باختيار رقم الإجابة الصحيحة فقط. "
    "أكتب الرقم فقط بلا شرح.\n\n"
    "{context}السؤال: {question}\n\n{choices}\n\nالإجابة:"
)


def parse_header(value):
    name, separator, header_value = value.partition("=")
    name = name.strip()
    if not separator or not name:
        raise argparse.ArgumentTypeError("header must be NAME=VALUE")
    return name, header_value


def build_prompt(item):
    choices = item["choices"].split(" ||| ")
    numbered = "\n".join(f"{j+1}. {c}" for j, c in enumerate(choices))
    ctx = (item.get("context") or "").strip()
    ctx = f"النص: {ctx}\n\n" if ctx else ""
    return PROMPT.format(context=ctx, question=item["question"],
                         choices=numbered), len(choices)


def ask_ollama(args, prompt, n_choices):
    import json
    import urllib.request
    schema = {"type": "object",
              "properties": {"answer": {"type": "integer",
                                        "minimum": 1, "maximum": n_choices}},
              "required": ["answer"]}
    body = json.dumps({
        "model": args.model.split("/", 1)[1],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": "30m",
        "format": schema,
        "options": {"temperature": 0, "num_predict": 24,
                    "seed": args.seed, "num_ctx": 2048},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=args.timeout) as r:
        return json.loads(r.read())["message"]["content"].strip()


def ask(completion, args, prompt, n_choices, max_tokens=None,
        force_answer_tool=False):
    if args.model.startswith("ollama_chat/") and not args.openai_compatible:
        return ask_ollama(args, prompt, n_choices)
    token_budget = args.max_tokens if max_tokens is None else max_tokens
    messages = [{"role": "user", "content": prompt}]
    if args.openai_compatible:
        kwargs = dict(
            model=args.model,
            messages=messages,
            max_completion_tokens=token_budget,
            timeout=args.timeout,
        )
        if force_answer_tool:
            answer_tool = {
                "type": "function",
                "function": {
                    "name": "submit_answer",
                    "description": "Submit the selected multiple-choice answer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "answer": {
                                "type": "integer",
                                "enum": list(range(1, n_choices + 1)),
                            },
                        },
                        "required": ["answer"],
                        "additionalProperties": False,
                    },
                },
            }
            kwargs["tools"] = [answer_tool]
            kwargs["tool_choice"] = {
                "type": "function",
                "function": {"name": "submit_answer"},
            }
    else:
        kwargs = dict(
            model=args.model,
            messages=messages,
            temperature=0,
            max_tokens=token_budget,
            timeout=args.timeout,
        )
        if args.api_base:
            kwargs["api_base"] = args.api_base
        if args.seed is not None:
            kwargs["seed"] = args.seed
    last = None
    for attempt in range(args.retries):
        try:
            response = completion(**kwargs)
            message = response.choices[0].message
            if force_answer_tool:
                for tool_call in message.tool_calls or []:
                    if tool_call.function.name == "submit_answer":
                        return tool_call.function.arguments.strip()
                return ""
            return (message.content or "").strip()
        except Exception as e:                                   # noqa: BLE001
            last = e
            msg = str(e).lower()
            fatal = any(w in msg for w in (
                "provider", "not found", "invalid", "api key", "unsupported",
                "badrequest", "authentication"))
            if fatal:
                raise SystemExit(f"\nSTOPPED: {type(e).__name__}: {e}\n")
            print(f"  retry {attempt+1}/{args.retries}: {type(e).__name__}: "
                  f"{str(e)[:120]}")
            time.sleep(min(2 ** attempt, 30))
    raise SystemExit(f"failed after {args.retries} attempts: {last}")


def parse_prediction(raw, n_choices):
    text = raw.strip()
    match = re.fullmatch(r'\{\s*"answer"\s*:\s*(\d+)\s*\}', text)
    if not match:
        match = re.fullmatch(r"(\d+)", text)
    if not match:
        return -1
    value = int(match.group(1))
    return value if 1 <= value <= n_choices else -1


def ask_and_parse(completion, args, prompt, n_choices):
    raw = ask(completion, args, prompt, n_choices)
    pred = parse_prediction(raw, n_choices)
    retry_max = args.unparsed_retry_max_tokens
    if pred != -1 or retry_max <= args.max_tokens:
        return raw, pred
    print(f"  unparseable response; retrying with {retry_max} tokens")
    raw = ask(completion, args, prompt, n_choices, max_tokens=retry_max)
    pred = parse_prediction(raw, n_choices)
    if pred == -1 and args.unparsed_use_answer_tool:
        print("  unparseable retry; forcing the answer tool")
        raw = ask(completion, args, prompt, n_choices, max_tokens=retry_max,
                  force_answer_tool=True)
        pred = parse_prediction(raw, n_choices)
    if pred == -1:
        raise SystemExit(
            f"unparseable response after retrying with {retry_max} tokens")
    return raw, pred


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--items", default=os.path.join(
        BASE, "audit-sample-400-master.csv"))
    p.add_argument("--api-base", default=None)
    p.add_argument("--openai-compatible", action="store_true")
    p.add_argument("--api-key-env")
    p.add_argument("--header", action="append", type=parse_header, default=[],
                   metavar="NAME=VALUE")
    p.add_argument("--max-tokens", type=int, default=8,
                   help="raise to ~256 for reasoning models")
    p.add_argument("--unparsed-retry-max-tokens", type=int, default=0,
                   help="retry an unparsed answer once at this larger budget")
    p.add_argument("--unparsed-use-answer-tool", action="store_true",
                   help="force a constrained answer tool after an unparsed retry")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--retries", type=int, default=5)
    p.add_argument("--seed", type=int, default=20260805)
    p.add_argument("--limit", type=int, default=0,
                   help="stop after N items (smoke test)")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()
    if (args.unparsed_retry_max_tokens
            and args.unparsed_retry_max_tokens <= args.max_tokens):
        p.error("--unparsed-retry-max-tokens must exceed --max-tokens")
    if (args.unparsed_use_answer_tool
            and not args.unparsed_retry_max_tokens):
        p.error("--unparsed-use-answer-tool requires "
                "--unparsed-retry-max-tokens")
    if args.unparsed_use_answer_tool and not args.openai_compatible:
        p.error("--unparsed-use-answer-tool requires --openai-compatible")
    if args.openai_compatible:
        if not args.api_base:
            p.error("--api-base is required with --openai-compatible")
        if not args.api_key_env:
            p.error("--api-key-env is required with --openai-compatible")
        if not os.environ.get(args.api_key_env):
            p.error(f"environment variable {args.api_key_env!r} must be "
                    "set and non-empty with --openai-compatible")

    completion = None
    if args.openai_compatible:
        from openai import OpenAI
        client = OpenAI(
            base_url=args.api_base,
            api_key=os.environ[args.api_key_env],
            default_headers=dict(args.header),
        )
        completion = client.chat.completions.create
    elif not args.model.startswith("ollama_chat/"):
        try:
            from litellm import completion
        except ImportError:
            sys.exit("run with: uv run python run_eval_litellm.py ...")

    out_path = os.path.join(BASE, f"results-{args.tag}.csv")
    done = set()
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            done = {r["item_id"] for r in csv.DictReader(f)}
        print(f"resuming: {len(done)} already answered")

    with open(args.items, encoding="utf-8") as f:
        items = list(csv.DictReader(f))
    total = len(items)

    new_file = not os.path.exists(out_path)
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["item_id", "subject", "source", "gold", "pred",
                        "correct", "raw"])
        for k, it in enumerate(items, 1):
            if it["item_id"] in done:
                continue
            prompt, n_choices = build_prompt(it)
            raw, pred = ask_and_parse(completion, args, prompt, n_choices)
            gold = int(it["gold_answer_index"]) + 1
            w.writerow([it["item_id"], it["subject"], it["source"], gold,
                        pred, int(pred == gold), raw.replace("\n", " ")[:80]])
            f.flush()
            if args.verbose:
                print(f"[{k}] gold={gold} pred={pred} raw={raw[:60]!r}")
            elif k % 25 == 0:
                print(f"{k}/{total}")
            if args.limit and k >= args.limit:
                break
    print(f"done -> {out_path}")


if __name__ == "__main__":
    main()
