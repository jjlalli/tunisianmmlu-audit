#!/usr/bin/env python3
"""Mechanical lower bound on Moroccan and orthographic contamination.

This complements the human annotation: it runs over all 21,500 items with no
annotator, so it is fully reproducible and covers the whole benchmark rather
than a 400-item sample. Every count is a LOWER bound -- a string match proves
contamination is present, but its absence proves nothing.

Reported alongside the annotated error rate, it answers the obvious reviewer
question "does your 400-item sample generalise?" without more annotation.

Run: python3 automatic_markers.py
"""

import glob
import os
import re

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "tmmlu-cache")

# Moroccan Darija forms with no currency in Tunisian Derja, and the Tunisian
# equivalent a native speaker would write instead.
MARKERS = [
    (r"\bالي\b", "الي", "اللي", "relativiser, single lām"),
    (r"\bغادي\b", "غادي", "باش / ماش", "future marker"),
    (r"\bديال", "ديال", "متاع", "possessive"),
    (r"گ", "گ", "ق / ڨ", "gāf — not a Tunisian letter"),
    (r"\bبغا\b", "بغا", "يحب", "to want"),
    (r"\bكاينين?\b", "كاين", "فما", "existential"),
    (r"\bدرت\b|\bديري\b|\bيدير\b", "دار/يدير", "عمل/يعمل", "to do"),
    (r"\bواخا\b", "واخا", "بهي / أوكي", "okay"),
]

# Moroccan present-tense verbal prefix كـ (كي-/كت-/كن-). Tunisian Derja marks
# the present with the bare imperfect and has no كـ prefix, so a كـ-prefixed
# verb is the single most reliable Moroccan signal in this corpus. Matched as a
# prefix rather than a word list, minus Tunisian and MSA words that begin with
# the same two letters.
PREFIX = r"\bك[يتن]\S{2,}"
PREFIX_EXCEPTIONS = (
    r"^(كيفاش|كيف|كيفية|كيما|كتاب|كتب|كتابة|كتابي|كتابات|كيلو|كيلومتر"
    r"|كيميا|كيميائ|كتل|كتلة|كتير|كثير|كيان|كينون|كنيسة|كتف|كتان)"
)

# Not dialect at all: artifacts of the export and normalisation pipeline.
ARTIFACTS = [
    (r"\bفيي\b", "فيي", "في with a doubled yāʾ (normalisation artifact)"),
    (r"\\n", r"\n", "literal backslash-n instead of a line break"),
]


def load():
    frames = []
    for path in sorted(glob.glob(os.path.join(CACHE, "*.parquet"))):
        df = pd.read_parquet(path)
        df["cfg"] = os.path.basename(path)[:-8]
        frames.append(df)
    if not frames:
        raise SystemExit("No cache found — run build-audit-sample.py first.")
    full = pd.concat(frames, ignore_index=True)
    full["item_id"] = full["cfg"] + "::" + full.groupby("cfg").cumcount().astype(str)
    return full


def main():
    full = load()
    text = (full["question"].astype(str) + "   "
            + full["choices"].apply(lambda c: " ".join(str(x) for x in c)))
    n = len(full)
    print(f"{n} items across {full['cfg'].nunique()} subjects\n")

    print("MOROCCAN MARKERS (question + choices)")
    print(f"  {'form':12s} {'Tunisian':14s} {'items':>7s} {'%':>7s}  note")
    hit = pd.Series(False, index=full.index)
    for pat, form, tun, note in MARKERS:
        m = text.str.contains(pat, regex=True)
        hit |= m
        print(f"  {form:12s} {tun:14s} {m.sum():7d} {100*m.sum()/n:6.2f}%  {note}")
    pre = text.apply(
        lambda t: any(not re.match(PREFIX_EXCEPTIONS, w)
                      for w in re.findall(PREFIX, t)))
    print(f"  {'كي-/كت-':12s} {'bare imperfect':14s} {pre.sum():7d} "
          f"{100*pre.sum()/n:6.2f}%  Moroccan present-tense prefix")
    hit |= pre
    print(f"\n  >>> at least one Moroccan marker: {hit.sum()} items "
          f"({100*hit.sum()/n:.2f}%)")

    print("\nPIPELINE ARTIFACTS")
    art = pd.Series(False, index=full.index)
    for pat, form, note in ARTIFACTS:
        m = text.str.contains(pat, regex=True)
        art |= m
        print(f"  {form:12s} {m.sum():7d} {100*m.sum()/n:6.2f}%  {note}")
    print(f"\n  >>> at least one artifact: {art.sum()} items "
          f"({100*art.sum()/n:.2f}%)")

    either = hit | art
    print(f"\n  >>> MECHANICALLY FLAGGED (either): {either.sum()} items "
          f"({100*either.sum()/n:.2f}%)")
    print("      This is a LOWER BOUND. A match proves contamination;")
    print("      no match proves nothing. Human annotation finds the rest.")

    print("\nBY SOURCE BENCHMARK")
    out = full.assign(flag=either).groupby("source")["flag"].agg(["sum", "count"])
    out["pct"] = (100 * out["sum"] / out["count"]).round(2)
    print(out.to_string())

    print("\nWORST 12 SUBJECTS")
    bysub = full.assign(flag=either).groupby("cfg")["flag"].agg(["sum", "count"])
    bysub["pct"] = (100 * bysub["sum"] / bysub["count"]).round(1)
    print(bysub.sort_values("pct", ascending=False).head(12).to_string())

    # ---- severity overlay (post-hoc, no re-annotation) -------------------
    # A binary interference label saturates on a corpus this contaminated.
    # Split flagged items by REPAIR COST instead:
    #   MORPHOLOGICAL  — Moroccan verbal morphology or function words woven
    #                    into the sentence (كي-/كت-/كن- prefixes, غادي+verb,
    #                    بغا, كاين): fixing means rewriting the sentence.
    #   LEXICAL        — isolated substitutable items (ديال, گ, واخا, يدير
    #                    forms, الي spelling): fixing is word swaps.
    # Classification is by regex and should be REVIEWED BY A NATIVE SPEAKER;
    # it is a triage heuristic, not a linguistic claim.
    morph = (pre
             | text.str.contains(r"\bغادي\b", regex=True)
             | text.str.contains(r"\bبغا\b", regex=True)
             | text.str.contains(r"\bكاينين?\b", regex=True))
    severity = pd.Series("clean", index=full.index)
    severity[either] = "lexical_or_artifact"
    severity[either & morph] = "morphological"

    print("\nSEVERITY OVERLAY (repair-cost triage, regex heuristic)")
    counts = severity.value_counts()
    for k in ("morphological", "lexical_or_artifact", "clean"):
        v = int(counts.get(k, 0))
        print(f"  {k:20s} {v:7d}  ({100*v/n:5.2f}%)")
    print("  morphological = Moroccan verb morphology present -> likely full"
          " rewrite;\n  lexical_or_artifact = word swaps / formatting -> cheap fix")

    print("\n  severity by source:")
    tab = pd.crosstab(full["source"], severity)
    print((100 * tab.div(tab.sum(axis=1), axis=0)).round(1).to_string())

    full.assign(flag=either, severity=severity)[
        ["item_id", "cfg", "source", "flag", "severity"]].to_csv(
        os.path.join(BASE, "automatic-markers.csv"), index=False)
    print("\nwritten: automatic-markers.csv "
          "(per-item flags + severity, joinable on item_id)")


if __name__ == "__main__":
    main()
