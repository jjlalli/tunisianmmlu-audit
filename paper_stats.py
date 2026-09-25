#!/usr/bin/env python3
"""Recompute every model-evaluation number in the paper from results-*.csv.

    python3 camera-ready/paper_stats.py                 # uses results-<tag>-corrected.csv
    python3 camera-ready/paper_stats.py --suffix -corrected-v2 --corrected-file camera-ready/audit-sample-400-corrected-v2.csv
    python3 paper_stats.py                              # from the repo root after the release

Prints: Table 2 (matched 389: orig, corr, delta from counts, flips), McNemar
exact p per model + Holm at .05, Table 3 (accuracy by adjudicated verdict band
on ORIGINAL text), Labess chance test, the two gap statements, and the
ESPRIT/Qwen gain by source benchmark. No third-party stats package needed.
"""
import argparse, csv, glob, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
# works both from mrl-audit/camera-ready/ (development) and from the repo root (release)
BASE = HERE if glob.glob(os.path.join(HERE, "results-*.csv")) else os.path.dirname(HERE)
ANN = next(p for p in (os.path.join(HERE, "annotations-400.csv"),
                       os.path.join(HERE, "camera-ready", "annotations-400.csv"),
                       os.path.join(BASE, "camera-ready", "annotations-400.csv"),
                       os.path.join(BASE, "annotations-400.csv")) if os.path.exists(p))
TAGS = [("gemini-3.1-pro", "Gemini 3.1 Pro"), ("gpt-5.6-sol", "GPT-5.6"),
        ("claude-sonnet-5", "Claude Sonnet 5"), ("qwen3", "Qwen3-8B"),
        ("esprit", "ESPRIT-Derja"), ("labess", "Labess-7B")]

def load(path):
    with open(path, encoding="utf-8") as f:
        return {r["item_id"]: r for r in csv.DictReader(f)}

def binom_two_sided(k, n):
    """Exact two-sided binomial test, p=0.5 (McNemar exact on discordant pairs)."""
    if n == 0: return 1.0
    pk = lambda x: math.comb(n, x) / 2**n
    p0 = pk(k)
    return min(1.0, sum(pk(x) for x in range(n+1) if pk(x) <= p0 + 1e-12))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--suffix", default="-corrected")
    ap.add_argument("--corrected-file", default=os.path.join(BASE, "audit-sample-400-corrected.csv"))
    a = ap.parse_args()
    ann = load(ANN)
    corr_items = load(a.corrected_file); ids = list(corr_items)  # 389
    verdict = {i: ann[i]["final_verdict"] for i in ann}
    source = {i: ann[i]["source"] for i in ann}
    print(f"matched set: {len(ids)} items\n")
    print(f"{'Model':16s} {'Orig':>6s} {'Corr':>6s} {'Delta':>6s} {'Flips':>6s} {'b(0->1)':>7s} {'c(1->0)':>7s} {'McNemar p':>10s}")
    pvals = {}; rows = {}
    for tag, name in TAGS:
        o = load(os.path.join(BASE, f"results-{tag}.csv")); c = load(os.path.join(BASE, f"results-{tag}{a.suffix}.csv"))
        miss = [i for i in ids if i not in o or i not in c]
        if miss: print(f"{name}: {len(miss)} matched items missing from a results file, skipped"); continue
        oc = sum(int(o[i]["correct"]) for i in ids); cc = sum(int(c[i]["correct"]) for i in ids)
        b = sum(1 for i in ids if o[i]["correct"] == "0" and c[i]["correct"] == "1")
        cn = sum(1 for i in ids if o[i]["correct"] == "1" and c[i]["correct"] == "0")
        p = binom_two_sided(min(b, cn), b + cn); pvals[name] = p
        rows[name] = (o, c)
        print(f"{name:16s} {100*oc/len(ids):6.1f} {100*cc/len(ids):6.1f} {100*(cc-oc)/len(ids):+6.1f} {b+cn:6d} {b:7d} {cn:7d} {p:10.3f}")
    # Holm
    print("\nHolm correction at .05 over the above-chance models (all except Labess):")
    items = sorted([(p, n) for n, p in pvals.items() if n != "Labess-7B"])
    m = len(items); sig = []
    for k, (p, n) in enumerate(items):
        thr = 0.05 / (m - k); ok = p <= thr
        print(f"  {n:16s} p={p:.3f}  threshold={thr:.4f}  {'significant' if ok else 'not'}")
        if not ok: break
        sig.append(n)
    print("  survive Holm:", sig or "none")
    # Table 3: bands on original text
    print(f"\n{'Model':16s} {'OK':>6s} {'FIX.':>6s} {'DISC.':>6s}   (original text; n = "
          f"{sum(1 for i in ann if verdict[i]=='OK')}/{sum(1 for i in ann if verdict[i]=='FIXABLE')}/{sum(1 for i in ann if verdict[i]=='DISCARD')})")
    for tag, name in TAGS:
        o = load(os.path.join(BASE, f"results-{tag}.csv"))
        def acc(v): s = [i for i in ann if verdict[i] == v and i in o]; return 100*sum(int(o[i]["correct"]) for i in s)/len(s)
        print(f"{name:16s} {acc('OK'):6.1f} {acc('FIXABLE'):6.1f} {acc('DISCARD'):6.1f}")
    # Labess chance
    o, c = rows.get("Labess-7B", (None, None))
    if o:
        k = sum(int(o[i]["correct"]) for i in ids); n = len(ids)
        exp = sum(1/len(corr_items[i]["choices"].split(" ||| ")) for i in ids)/n
        # two-sided exact binomial test at p=exp (the paper reports the two-sided value)
        pk = lambda x: math.comb(n, x)*exp**x*(1-exp)**(n-x)
        p0 = pk(k); p1 = min(1.0, sum(pk(x) for x in range(n+1) if pk(x) <= p0 + 1e-12))
        flips = sum(1 for i in ids if o[i]["correct"] != c[i]["correct"])
        print(f"\nLabess: {k} of {n} correct ({100*k/n:.1f}%), chance {100*exp:.1f}%, two-sided binomial p={p1:.2f}; {flips} items ({100*flips/n:.1f}%) change correctness")
    # gaps and by-source gains
    def acc_on(res, S): return 100*sum(int(res[i]["correct"]) for i in S)/len(S)
    if all(n in rows for n in ("Qwen3-8B", "ESPRIT-Derja", "GPT-5.6", "Gemini 3.1 Pro")):
        q, e, g, ge = rows["Qwen3-8B"], rows["ESPRIT-Derja"], rows["GPT-5.6"], rows["Gemini 3.1 Pro"]
        print(f"\nQwen3 lead over ESPRIT: orig {acc_on(q[0],ids)-acc_on(e[0],ids):+.1f}  corr {acc_on(q[1],ids)-acc_on(e[1],ids):+.1f}")
        print(f"GPT-5.6 deficit to Gemini: orig {acc_on(ge[0],ids)-acc_on(g[0],ids):.1f}  corr {acc_on(ge[1],ids)-acc_on(g[1],ids):.1f}")
        for name in ("ESPRIT-Derja", "Qwen3-8B"):
            o, c = rows[name]
            for src in ("arabic_mmlu", "mmlu"):
                S = [i for i in ids if source[i] == src]
                print(f"  {name:13s} {src:12s} n={len(S):3d}  orig {acc_on(o,S):5.1f}  corr {acc_on(c,S):5.1f}  gain {acc_on(c,S)-acc_on(o,S):+.1f}")

if __name__ == "__main__":
    main()
