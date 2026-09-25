# TunisianMMLU-Verified

Native-speaker audit of [linagora/TunisianMMLU](https://huggingface.co/datasets/linagora/TunisianMMLU), a machine-translated MMLU-style benchmark for Tunisian Arabic (Derja).

Paper: *Is TunisianMMLU Actually Tunisian? A Native-Speaker Audit of a Machine-Translated Dialect Benchmark*, MRL 2026 (EMNLP workshop), Budapest. [ACL Anthology link to be added when the proceedings are out.]

Hugging Face mirror of the data files: https://huggingface.co/datasets/HF-USER/TunisianMMLU-Verified

Every artifact is keyed to the original item identifier `subject::row` (row index within the subject's test split, as downloaded in August 2026), so corrections and flags can be merged upstream rather than forking the benchmark.

## What is here

| File | What it is | Licence |
|---|---|---|
| `audit-sample-400-master.csv` | The 400 audited items as released by TunisianMMLU (stratified over 44 subjects, seed 20260805, floor 4 per subject). | CC BY-NC-SA 4.0 (inherited) |
| `annotations-400.csv` | Per-item labels from both annotators (six binary criteria, verdict, error origin), the adjudicated final verdict and origin, and annotator A's raw correction field. | CC BY 4.0 |
| `audit-sample-400-corrected.csv` | The 389-item corrected subset exactly as evaluated in the paper (corrected text for the 333 FIXABLE items, unchanged text for the 56 OK items, 11 DISCARD items excluded). For 173 items the annotator's corrected option list sits inside the `question` field after `|||` and the `choices` field still holds the original options; see the note below. | CC BY-NC-SA 4.0 (derived) |
| `audit-sample-400-corrected-repaired.csv` | The same subset with those 173 items split back into `question` and `choices` (corrected question for 329 items, corrected options for 172). Not used for the numbers in the paper. | CC BY-NC-SA 4.0 (derived) |
| `automatic-markers.csv` | Corpus-wide flag and repair-cost severity for all 21,500 items. | CC BY 4.0 |
| `automatic_markers.py` | The scanner: patterns, exclusion list, counts. Running it reproduces `automatic-markers.csv` and the 63.4% corpus figure in the paper. | MIT |
| `annotation-guideline.md` | The guideline given to both annotators, with worked examples drawn from outside the sample. | CC BY 4.0 |
| `prefix-spotcheck-30.csv` | The 30 prefix-only flagged items checked by annotator A. | CC BY 4.0 |
| `build-audit-sample.py` | Downloads the benchmark and rebuilds the sample. | MIT |
| `run_eval_litellm.py`, `score.py`, `paper_stats.py`, `run_all.sh` | Evaluation harness and the script that recomputes every model number in the paper. | MIT |
| `results-<model>.csv`, `results-<model>-corrected.csv` | Per-item model answers on original and corrected text. | CC BY 4.0 |

**Note on the corrected file.** The model runs reported in the paper used `audit-sample-400-corrected.csv` as it is here. For 173 of the 333 FIXABLE items that file carries the corrected options inside the question field, so the evaluation prompt for those items contained the corrected option list followed by the original one. Gains between original and corrected text are of the same size on those 173 items and on the 160 correctly formatted ones for every model. `audit-sample-400-corrected-repaired.csv` is the clean version for future use.

`annotations-400.csv` columns: `A_*` and `B_*` are the two independent passes (1 = pass, 0 = fail on each criterion); `final_verdict` / `final_origin` are post-adjudication; `adjudicated` marks the 119 items whose three-way verdict differed between annotators.

## Reproduce

```bash
uv sync --locked
python3 build-audit-sample.py            # downloads the 44 parquet files (~4 MB)
python3 automatic_markers.py             # corpus scan, writes automatic-markers.csv
python3 paper_stats.py                   # Tables 2 and 3, McNemar, Holm, gap figures
```

Model runs (see the docstring of `run_eval_litellm.py` for the exact commands per backend):

```bash
uv run python run_eval_litellm.py --model openai/gpt-5.6-sol --tag gpt-5.6-sol --max-tokens 256
uv run python run_eval_litellm.py --model openai/gpt-5.6-sol --tag gpt-5.6-sol-corrected --max-tokens 256 --items audit-sample-400-corrected.csv   # as in the paper
```

## Citation

```bibtex
@inproceedings{jlali-suppa-2026-tunisianmmlu,
  title     = {Is {T}unisian{MMLU} Actually {T}unisian? A Native-Speaker Audit of a Machine-Translated Dialect Benchmark},
  author    = {Jlali, Fatma Ezzahra and {\v{S}}uppa, Marek},
  booktitle = {Proceedings of the 6th Workshop on Multilingual Representation Learning (MRL 2026)},
  year      = {2026},
  address   = {Budapest, Hungary},
  publisher = {Association for Computational Linguistics}
}
```

## Licences

Three licences apply, by file, as listed above. The corrected Derja text is a derivative of TunisianMMLU and carries its CC BY-NC-SA 4.0 licence. Labels, flags, the guideline and the result files are newly authored and released under CC BY 4.0. Code is MIT. See `LICENSE-code`, `LICENSE-labels`, `LICENSE-corrected-text`.
