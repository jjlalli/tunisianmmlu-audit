# TunisianMMLU audit: annotation guideline

The instructions given to the two annotators on 5 August 2026. Label definitions, verdict rules and worked examples are unchanged; scheduling notes and the annotators' personal details have been removed. The counts in the marker table were computed over the question field only, before the corpus scanner was finalised; the released scanner (`automatic_markers.py`) counts the question and the options together, which is why the paper reports larger figures (for example 624 items with فيي and 456 with a literal `\n`).

Two annotators, same 400 items, same order, independently. **Never look at the
other person's sheet while annotating.** Disagreements are settled by annotator A
after both finish; that is the adjudication step, not a discussion during annotation.

For every item: read question + context + choices, then set each of the six
labels to **1 (pass) or 0 (fail)**. Then one verdict, then (only if FIXABLE)
write the corrected Derja.

## Worked examples

**Every example below is from an item OUTSIDE the 400.** That is deliberate: if a
sampled item were used here with its "correct" label given away, the two
annotators agreeing on it afterwards would prove nothing.

### The Moroccan markers, and what Tunisian uses instead

These are the things to look for on `msa_moroccan_interference`. Counts are
across the whole 21,500-item benchmark, so this is what to expect:

| Moroccan form | Tunisian equivalent | Items affected |
|---|---|---|
| `الي` (single lām) | `اللي` | 2,346 — **10.9%** |
| `غادي` (future) | `باش` / `ماش` | 1,967 — **9.2%** |
| `ديال` (possessive) | `متاع` | 555 — 2.6% |
| `گ` (gāf, not a Tunisian letter) | `ق` / `ڨ` | 426 — 2.0% |
| `بغا` (to want) | `يحب` | 182 — 0.9% |
| `كاين` (there is) | `فما` | 160 — 0.7% |
| `كي-` / `كت-` verb prefixes | no prefix, or `ن-` | very common |

**Example — `msa_moroccan_interference = 0`** (`high_school_european_history::12`):

> **غادي** تعطيني الحق باش تتفكر، بلي دايما كنت **كن**دافع بقوة على حق كل واحد في الرأي متاعو

`غادي` + `كندافع` — future and present marked the Moroccan way. A Tunisian
would write `باش تعطيني` and `نـدافع`.

**Example — `orthographic_naturalness = 0`** (`islamic_studies::1176`):

> معنى كلمة اليتيم … choices: «**الي** كيطلب الفلوس من الناس» / «**الي** ماتت لو مو وهو صغير»

`الي` for `اللي`, twice. The word is authentic Tunisian; the spelling is not.
So **authenticity can be 1 while orthography is 0** — that pair is the most
common combination you'll hit.

### Two formatting defects that are not your fault and not the language's

`فيي` instead of `في` — a doubled yāʾ from the normalisation step. **442 items
(2.1%).** Mark `orthographic_naturalness = 0`.

Literal `\n` printed inside the text instead of a line break. **452 items
(2.1%)**, worst in nutrition (118) and high_school_world_history (52). Mark
`orthographic_naturalness = 0` and note it; it is a data-export bug.

### `answer_preservation = 0` — the clearest case

**Example** (`islamic_studies::286`):

> شنوّة سميت أم النبي اسماعيل عليه السلام؟
> choices: **مريم · مريم** · هاجر · سارة — gold: هاجر

`مريم` appears twice. The gold answer is still right, but the options are
broken, so the item cannot be scored fairly. **And this one is
`error_origin = SOURCE`** — the duplicate came from ArabicMMLU's own parsing,
not from NLLB. Exactly the distinction that column exists for.

### `semantic_fidelity = 0` — an item that isn't a question

**Example** (`islamic_studies::74`):

> عرقلة اللعب المنافس
> choices: كيعجبني · ما كيعجبنيش

A noun phrase with like/dislike options, filed under Islamic studies. Nothing
here is answerable. Also `كيعجبني` is Moroccan, so this fails two labels at
once — that is normal and expected.

### The trap: an item that LOOKS broken and isn't

**Example** (`islamic_studies`, one of the blue rows of the annotation sheet):

> **question:** النص اللي قبل هو
> **context:** اللهم صلي على محمد، وعلى آل محمد، كيما صليتي على آل إبراهيم…

"The preceding text is —" reads like garbage until you read the `context`
column. **All six labels can be 1 here.** Eleven rows in the sheet are like
this and they are shaded blue with a warning. Marking them broken would
manufacture eleven false errors, all inside one subject.

### The judgment call: culturally foreign ≠ culturally invalid

**944 items (4.4%) of the benchmark explicitly reference the United States.**
For instance a moral-scenarios item asking what is wrong "حسب المعايير
الأخلاقية العادية في الولايات المتحدة" — by ordinary US moral standards.

That is **`cultural_validity = 1`**. It is foreign, but it states its own frame
and a Tunisian can answer it. Reserve `0` for items whose premise silently
breaks — one that assumes an institution, price, law or season that does not
exist here, without saying which country it means.

Technical terms left in Latin script (`ANOVA`, `MANOVA`, `SAT`) are also
**not** failures. Tunisians write those in Latin too.

## The six labels

**semantic_fidelity** — Does the question still ask a coherent, answerable
thing? 0 if the translation garbled the meaning, dropped a needed word, or the
question no longer makes sense on its own.

**answer_preservation** — Given this Derja text, is the marked gold answer
still the single correct choice? 0 if the translation changed the meaning so
another choice becomes right, the gold becomes wrong, or two choices became
identical.

**tunisian_authenticity** — Would a Tunisian actually say it this way? 0 if
the sentence is grammatical Arabic but no Tunisian would produce it.
(This is about the whole sentence; single foreign words go under interference.)

**msa_moroccan_interference** — 1 = clean of intrusions. 0 if it contains
Moroccan features (كي-/كت- verb prefixes, گ, جوج, ديال, غادي, داك الشي…) or
long stretches of pure MSA where Derja should be. Expect this to fire often.

**orthographic_naturalness** — Is the spelling how Tunisians write Derja? 0
for impossible spellings, broken characters, or transliteration artifacts.
(A word can be authentic Tunisian but misspelled: authenticity 1, orthography 0.)

**cultural_validity** — Does the content make sense for a Tunisian context
where the question implies one? Most factual items pass automatically; 0 is
for items whose premise breaks in a Tunisian setting.

## Verdict (one per item)

- **OK** — all six labels 1, item usable as-is.
- **FIXABLE** — something failed but a local rewrite repairs it → fill
  `corrected_derja` with the full corrected question (and corrected choices
  after `|||` separators if a choice needed fixing).
- **DISCARD** — not repairable without re-translating from scratch (garbled
  meaning, broken answer). Do NOT spend time rewriting these.

Rule of thumb: if fixing takes more than ~90 seconds, it's a DISCARD.

## error_origin — ONLY when the verdict is not OK

MMLU itself has an estimated 6.49% error rate (Gema et al., "Are We Done
with MMLU?", MMLU-Redux), so some items were defective before anyone translated
them. This label separates those from the damage done by translation.

- **TRANSLATION** — this item would be fine in correct Derja. The damage is
  in the language: Moroccan forms, MSA leakage, garbled wording, impossible
  spelling, a choice that lost its meaning in translation.
- **SOURCE** — this item would be broken in ANY language. Two identical
  choices, no correct answer among the options, a question that isn't a
  question, an answer key that cannot be right regardless of wording.
- **UNCLEAR** — genuinely cannot tell. Use it freely; a large UNCLEAR share
  is itself an honest finding, and guessing here is worse than admitting it.

Judge from the Derja alone. Do not go looking for the English original —
that would make the two annotators non-independent and cost hours.

## Order of work

Seed 20260805, sample built by `build-audit-sample.py`; both annotators work
in `annotation_order`. If an annotator stops early, everything up to the last
completed item is still a valid random sample.
