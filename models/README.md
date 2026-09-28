# Deployed model files

These two files are tracked by git on purpose, the one exception to the
`data/` folder's usual gitignore rule.

Render builds the API from a fresh copy of this repository with no
persistent disk, so whatever it loads at startup has to already be
committed. `src/serve/api.py` loads both files directly.

- `surrogate.joblib`: the Gaussian process surrogate from Phase 4,
  retrained on extra points near the optimum corner. The most accurate
  surrogate found, both overall and at that corner, see `phase4_plan.md`.
- `winder_rul.joblib`: the twin's own remaining life model from Phase 6.

Regenerate both with `python src/serve/export_models.py` whenever the
underlying training data or model choice changes, so this folder never
drifts out of sync with the code that produced it.
