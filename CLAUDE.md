# Coffee Roast Advisor — project notes for Claude Code

uv project; run everything with `uv run` (CLI entry points: ingest, design,
plan, report, capture, fakemeter, live, replay). Tests: `uv run pytest` —
they run against the real archive in `data/raw/training_data/` and the real
serial captures in `tests/fixtures/`; keep it that way (no synthetic-only
fixtures for things real files can cover).

Hard-won rules — do not re-derive (full reasoning in docs/PROJECT_BRIEF.md):

- `.alog` files are Python dict literals: `ast.literal_eval`, never JSON.
  All decoding lives in `src/roast_advisor/alog.py` only — including the
  dial formula `round((v-1)*10/11)` and THE charge-detection rule
  (`detect_charge`), which live and offline code must share.
- Never fit or plan on excluded probe-cohort roasts (`data/cohort_labels.json`;
  ingest auto-flags FCs-BT outliers >30°F from median).
- RoR always from ±10–20s regression windows, never raw 2s differences.
- The planner is kNN behavior-cloning by design; a pooled linear thermal
  model is unidentifiable on this history (power ~ BT collinearity). Don't
  "upgrade" it to regression without calibration-roast data.
- The live advisor must stay deterministic (no model/API calls at roast
  time) and its replay transcript must match the live path exactly (tested).
- Design targets anchor in published roasting knowledge (see the /design-roast
  skill's REFERENCE.md); the user's archive is only the machine model.
  Temps are rig-relative — anchor to the rig's measured first crack
  (~392–397°F on the author's SR800), never copy absolute temps across rigs.

Community data lands in `data/raw/community/<handle>/`; ingest is idempotent
(upserts by roastUUID) so re-running over everything is always safe.
