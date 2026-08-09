#!/usr/bin/env python3
"""Aggregate results-*.csv into the paper's tables.

    python3 score.py

Reads every results-<tag>.csv in this folder. A file named
results-<tag>-corrected.csv is treated as the corrected-text run of <tag>
and paired with it. Writes summary-accuracy.csv and summary-ranking.csv.
"""

import csv
import glob
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def stats(rows):
    n = len(rows)
    if not n:
        return None
    correct = sum(int(r["correct"]) for r in rows)
    refused = sum(1 for r in rows if r["pred"] == "-1")
    by_source = {}
    for r in rows:
        s = r["source"]
        a, b = by_source.get(s, (0, 0))
        by_source[s] = (a + int(r["correct"]), b + 1)
    return {
        "n": n,
        "acc": 100 * correct / n,
        "refusal": 100 * refused / n,
        "by_source": {k: 100 * a / b for k, (a, b) in by_source.items()},
    }


def main():
    runs = {}
    for path in sorted(glob.glob(os.path.join(BASE, "results-*.csv"))):
        tag = os.path.basename(path)[len("results-"):-len(".csv")]
        kind = "corrected" if tag.endswith("-corrected") else "original"
        if kind == "corrected":
            tag = tag[:-len("-corrected")]
        runs.setdefault(tag, {})[kind] = stats(load(path))

    if not runs:
        raise SystemExit("no results-*.csv found")

    sources = sorted({s for t in runs.values() for v in t.values() if v
                      for s in v["by_source"]})

    print(f"{'model':14s} {'run':10s} {'n':>5s} {'acc':>7s} {'refuse':>7s} "
          + " ".join(f"{s:>13s}" for s in sources))
    rows_out = []
    for tag in sorted(runs):
        for kind in ("original", "corrected"):
            v = runs[tag].get(kind)
            if not v:
                continue
            print(f"{tag:14s} {kind:10s} {v['n']:5d} {v['acc']:6.1f}% "
                  f"{v['refusal']:6.1f}% "
                  + " ".join(f"{v['by_source'].get(s, float('nan')):12.1f}%"
                             for s in sources))
            rows_out.append([tag, kind, v["n"], round(v["acc"], 2),
                             round(v["refusal"], 2)]
                            + [round(v["by_source"].get(s, 0), 2)
                               for s in sources])

    with open(os.path.join(BASE, "summary-accuracy.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "run", "n", "accuracy", "refusal_rate"] + sources)
        w.writerows(rows_out)

    paired = {t: v for t, v in runs.items()
              if v.get("original") and v.get("corrected")}
    if not paired:
        print("\n(no corrected runs yet — ranking table skipped)")
        return

    def ranking(kind):
        order = sorted(paired, key=lambda t: -paired[t][kind]["acc"])
        return {t: i + 1 for i, t in enumerate(order)}

    r_orig, r_corr = ranking("original"), ranking("corrected")
    print(f"\n{'model':14s} {'orig':>7s} {'corr':>7s} {'delta':>7s} "
          f"{'rank_o':>7s} {'rank_c':>7s} {'move':>6s}")
    out = []
    for t in sorted(paired, key=lambda t: r_orig[t]):
        o = paired[t]["original"]["acc"]
        c = paired[t]["corrected"]["acc"]
        move = r_orig[t] - r_corr[t]
        print(f"{t:14s} {o:6.1f}% {c:6.1f}% {c-o:+6.1f} "
              f"{r_orig[t]:7d} {r_corr[t]:7d} {move:+6d}")
        out.append([t, round(o, 2), round(c, 2), round(c - o, 2),
                    r_orig[t], r_corr[t], move])

    with open(os.path.join(BASE, "summary-ranking.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "acc_original", "acc_corrected", "delta",
                    "rank_original", "rank_corrected", "rank_move"])
        w.writerows(out)

    swaps = sum(1 for r in out if r[6] != 0)
    print(f"\nmodels changing rank: {swaps} of {len(out)}")


if __name__ == "__main__":
    main()
