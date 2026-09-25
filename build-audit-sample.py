#!/usr/bin/env python3
"""Build the 400-item TunisianMMLU audit sample. Run: python3 build-audit-sample.py
Needs: pip install pandas pyarrow requests
Downloads the 44 test parquets (~4 MB), prints the source-by-subject crosstab,
builds the stratified sample (floor 4 per subject, remainder proportional,
seed 20260805), and writes the annotation sheets next to this script."""

import os
import random
import sys
import time

import pandas as pd
import requests

SEED = 20260805
N_TARGET = 400
FLOOR = 4
BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "tmmlu-cache")

CONFIGS = [
    "accounting", "arabic_language", "arabic_language_(general)",
    "arabic_language_(grammar)", "biology", "civics", "computer_science",
    "driving_test", "economics", "general_knowledge", "geography",
    "global_facts", "high_school_european_history", "high_school_geography",
    "high_school_government_and_politics", "high_school_psychology",
    "high_school_statistics", "high_school_world_history", "history",
    "human_aging", "international_law", "islamic_studies", "jurisprudence",
    "law", "logical_fallacies", "management", "management_ar", "marketing",
    "math", "moral_disputes", "moral_scenarios", "natural_science",
    "nutrition", "philosophy", "philosophy_ar", "physics",
    "political_science", "professional_law", "professional_psychology",
    "public_relations", "security_studies", "social_science", "sociology",
    "world_religions",
]

GROUPS = {
    "STEM/health": [
        "biology", "computer_science", "math", "physics", "natural_science",
        "high_school_statistics", "nutrition", "human_aging", "global_facts",
    ],
    "humanities/history": [
        "history", "high_school_european_history", "high_school_world_history",
        "geography", "high_school_geography", "philosophy", "philosophy_ar",
        "logical_fallacies", "sociology", "social_science",
        "high_school_psychology", "professional_psychology",
    ],
    "islamic/moral": [
        "islamic_studies", "jurisprudence", "world_religions",
        "moral_disputes", "moral_scenarios",
    ],
    "language": [
        "arabic_language", "arabic_language_(general)",
        "arabic_language_(grammar)",
    ],
    "professional/civic": [
        "accounting", "economics", "management", "management_ar", "marketing",
        "public_relations", "law", "professional_law", "international_law",
        "civics", "political_science", "high_school_government_and_politics",
        "security_studies", "driving_test", "general_knowledge",
    ],
}
GROUP_OF = {s: g for g, subs in GROUPS.items() for s in subs}
assert sorted(GROUP_OF) == sorted(CONFIGS), "group map does not cover configs"


def cached_ok(path):
    """A cache file counts only if it exists AND actually opens."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    try:
        pd.read_parquet(path)
        return True
    except Exception:
        os.remove(path)
        return False


def fetch_one(session, cfg, path, attempts=6):
    """Stream to a .part file, then rename. Retries with backoff.
    Slow/flaky connections are expected -- nothing here is fatal."""
    url = ("https://huggingface.co/datasets/linagora/TunisianMMLU/"
           f"resolve/main/{cfg}/test-00000-of-00001.parquet")
    part = path + ".part"
    for attempt in range(1, attempts + 1):
        try:
            with session.get(url, timeout=(15, 180), stream=True) as r:
                r.raise_for_status()
                with open(part, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
            os.replace(part, path)
            if cached_ok(path):
                return True
            print(f"    {cfg}: downloaded but unreadable, retrying")
        except Exception as exc:
            wait = min(2 ** attempt, 30)
            print(f"    {cfg}: attempt {attempt}/{attempts} failed "
                  f"({type(exc).__name__}), retrying in {wait}s")
            time.sleep(wait)
        finally:
            if os.path.exists(part):
                os.remove(part)
    return False


def download():
    os.makedirs(CACHE, exist_ok=True)
    session = requests.Session()
    todo = [c for c in CONFIGS
            if not cached_ok(os.path.join(CACHE, f"{c}.parquet"))]
    have = len(CONFIGS) - len(todo)
    if have:
        print(f"  {have}/{len(CONFIGS)} already cached, skipping those")

    failed = []
    for i, c in enumerate(todo, 1):
        print(f"  [{i}/{len(todo)}] {c} ...")
        if not fetch_one(session, c, os.path.join(CACHE, f"{c}.parquet")):
            failed.append(c)

    if failed:
        print("\n" + "=" * 60)
        print(f"COULD NOT DOWNLOAD {len(failed)} of {len(CONFIGS)}: "
              + ", ".join(failed))
        print("Your connection dropped. Everything else is cached --")
        print("just run this script again and it resumes from here.")
        print("=" * 60)
        sys.exit(1)

    frames = {}
    for c in CONFIGS:
        df = pd.read_parquet(os.path.join(CACHE, f"{c}.parquet"))
        df["subject_cfg"] = c
        frames[c] = df
    return frames


def main():
    frames = download()
    full = pd.concat(frames.values(), ignore_index=True)
    print(f"\ntotal test items: {len(full)}")
    print("source values:", sorted(full["source"].astype(str).unique()))

    cross = pd.crosstab(full["subject_cfg"], full["source"])
    cross.to_csv(os.path.join(BASE, "source-by-subject.csv"))
    mixed = cross[(cross > 0).sum(axis=1) > 1]
    print("\nsubjects containing MORE THAN ONE source (usable for the "
          "within-subject english-vs-msa comparison):")
    print(mixed if len(mixed) else "  NONE -- source and subject are fully "
          "confounded; the source comparison must be reported as descriptive")

    sizes = {c: len(frames[c]) for c in CONFIGS}
    total = sum(sizes.values())
    pool = N_TARGET - FLOOR * len(CONFIGS)
    exact = {c: FLOOR + pool * sizes[c] / total for c in CONFIGS}
    alloc = {c: int(exact[c]) for c in CONFIGS}
    remainders = sorted(CONFIGS, key=lambda c: exact[c] - alloc[c],
                        reverse=True)
    for c in remainders[: N_TARGET - sum(alloc.values())]:
        alloc[c] += 1
    assert sum(alloc.values()) == N_TARGET

    rng = random.Random(SEED)
    rows = []
    for c in CONFIGS:
        take = min(alloc[c], sizes[c])
        for i in sorted(rng.sample(range(sizes[c]), take)):
            r = frames[c].iloc[i]
            choices = list(r["choices"])
            rows.append({
                "item_id": f"{c}::{i}",
                "subject": c,
                "domain_group": GROUP_OF[c],
                "source": r["source"],
                "question": r["question"],
                "context": r["context"],
                "choices": " ||| ".join(map(str, choices)),
                "gold_answer_index": int(r["answer"]),
                "gold_answer_text": str(choices[int(r["answer"])]),
            })
    sample = pd.DataFrame(rows)
    sample = sample.sample(frac=1, random_state=SEED).reset_index(drop=True)
    sample.insert(0, "annotation_order", range(1, len(sample) + 1))
    sample.to_csv(os.path.join(BASE, "audit-sample-400-master.csv"),
                  index=False)

    labels = ["semantic_fidelity", "answer_preservation",
              "tunisian_authenticity", "msa_moroccan_interference",
              "orthographic_naturalness", "cultural_validity"]
    sheet = sample.copy()
    for col in labels:
        sheet[col] = ""
    sheet["verdict"] = ""            # OK / FIXABLE / DISCARD
    sheet["error_origin"] = ""       # TRANSLATION / SOURCE / UNCLEAR
    sheet["corrected_derja"] = ""
    sheet["notes"] = ""
    for who in ("A", "B"):
        sheet.to_csv(os.path.join(BASE, f"annotator-{who}.csv"), index=False)

    print(f"\nsample written: {len(sample)} items, seed {SEED}")
    print(sample.groupby("domain_group").size().to_string())
    print(sample.groupby("source").size().to_string())
    print("\nfiles: audit-sample-400-master.csv, annotator-A.csv, "
          "annotator-B.csv, source-by-subject.csv")


if __name__ == "__main__":
    sys.exit(main())
