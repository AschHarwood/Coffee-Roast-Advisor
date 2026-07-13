# Roast Advisor — Project Brief for Claude Code

## Goal

A workflow where the roaster (Asch) designs a roast profile from high-level constraints
(charge/preheat, turning point, first crack temp, drop temp, total time, development ratio)
and the software generates a **machine settings plan** ("cue card") predicted from his own
roast history. After each roast, the new `.alog` is ingested, the plan is scored against the
target, and predictions improve.

No live/real-time software is required for v1. The loop is:

1. **Design**: constraints → ideal BT/RoR curve.
2. **Plan**: curve + historical dataset → predicted fan/power schedule (cue card).
3. **Roast**: follow the card, log fan/power changes as Artisan events as usual.
4. **Ingest + score**: parse the new `.alog`, overlay actual vs designed curve, report
   deviations, refine.

Current machine: **Fresh Roast SR800** (fan 1–9, power 1–9), logged via Artisan
(Mastech MS6514 thermocouple meter, serial `/dev/cu.SLAB_USBtoUART`, 9600 baud, macOS M1).
Future machine: **Yoshan 2kg gas** (manual gas valve — same event-logging approach, one
"gas" slider instead of fan/power; expect ~30–60s thermal lag vs ~10–30s on the SR800).

## What already exists (prototypes in this folder)

- `roast_advisor.py` — parses `.alog`, prints a settings plan from a target roast,
  and replays a past roast against a target showing what an advisor would have recommended
  (`plan` and `replay` modes). The `advise()` function is designed to be callable in real
  time later.
- `profile_designer.py` — builds an ideal BT/RoR curve from constraints and predicts
  fan/power settings via kNN over historical (BT, RoR) samples. Produced `cue_card.txt`
  and `designed_profile_plan.png`.
- `parse_alog.py`, `response_analysis.py`, `fit_model.py`/`fit_model2.py` — exploration
  scripts (event extraction, step-response analysis, linear thermal model attempts).

These are prototypes: refactor freely, but preserve the `.alog` decoding details below.

## .alog format notes (validated against 7 real files)

`.alog` files are Python dict literals — parse with `ast.literal_eval`, **not** JSON.

Key fields:

- `timex`: list of sample times (s). Sampling interval ~2.0s. `temp1` = ET (often -1.0,
  no ET probe on SR800), `temp2` = BT (°F, `mode` == 'F').
- `timeindex`: `[CHARGE, DRY, FCs, FCe, SCs, SCe, DROP, COOL]` — **indices into timex**,
  -1/0 when not marked. Some roasts lack CHARGE and/or DROP marks; handle gracefully
  (CHARGE missing → treat t=0 as charge; DROP missing → use last sample).
- Control events: `specialevents` (index into timex), `specialeventstype` (index into
  `etypes`, e.g. `['fan','power','Damper','Burner','--']` — **case varies**, lowercase
  before matching), `specialeventsvalue`, `specialeventsStrings`.
  - **Value decoding**: Artisan stores slider value as `v/10 + 1`. So dial setting =
    `round((value - 1) * 10 / 11)` for this user's 1–9 dials (raw decoded values come out
    as 11,22,...,99).
- Metadata worth keeping: `title`, `beans`, `weight` (g/lb + unit), `ambientTemp`,
  `ambient_humidity`, `roastisodate`, `roastepoch`, `roastUUID`, `roastbatchnr`,
  `computed` (Artisan's own derived stats — useful cross-check).

Known data quirks found in the sample set:

- Two roasts from 2024-03 read ~90°F hotter at first crack (~484–494°F vs ~386–396°F) —
  probe placement/config difference. The ingest pipeline must support **excluding or
  tagging** such cohorts; mixing them silently corrupts the model. Heuristic: flag any
  roast whose FCs BT is >30°F from the rolling cohort median; ask the user rather than
  guessing.
- Fan and power are usually changed as a pair 2s apart (two slider moves).
- Early samples (pre-charge / BT < 150°F) are noisy; exclude from model fitting.

## Findings so far (don't re-learn these the hard way)

1. **Naive step-response analysis is confounded**: the operator raises power *because*
   RoR is falling, so before/after comparisons show power increases "lowering" RoR.
2. **A pooled linear model (`dBT/dt = c0 + c1·P + c2·F + c3·BT`) is unidentifiable on this
   history**: the roasts are so consistent that power correlates almost perfectly with BT,
   so `c1` is unstable (came out ≈0 or negative; inverting for P gives nonsense).
   High R² (0.90) does not mean the causal effect is captured.
3. **What works now**: kNN over historical `(BT, RoR) → (fan, power)` samples. Because
   it interpolates the operator's demonstrated behavior, it's reliable near historical
   profiles and degrades gracefully. Validated by leave-one-out replay: recommendations
   matched actual settings at most checkpoints, and both roasts hit FCs within seconds
   of each other.
4. **To get a real causal model** (needed for aggressive/novel profiles and for the
   Yoshan): run 2–3 **calibration roasts** with deliberate excitation — hold power
   constant through a phase where it would normally ramp, make an isolated ±2 power step
   with no fan change and hold 90s, etc. Cheap/sacrificial beans. Then fit a constrained
   physical model, e.g. `dBT/dt = k(F) · (T_eq(P, F) − BT)`, with a sign prior on the
   power effect. Rough current estimates: 1 power step ≈ 3–6 F/min RoR change; response
   begins ~10–40s after the change on the SR800.

## Proposed repo layout

```
roast-advisor/
  README.md                  (this file, evolved)
  data/
    raw/                     .alog archive (gitignored if large)
    roasts.parquet           per-roast metadata table
    samples.parquet          per-sample long table
  src/
    alog.py                  .alog parsing/decoding (single source of truth)
    ingest.py                scan raw/, parse, validate, upsert into parquet by roastUUID
    dataset.py               load/join tables, cohort filters, (BT, RoR, fan, power) samples
    designer.py              constraints -> target BT/RoR curve
    planner.py               target curve + dataset -> cue card (kNN now; model later)
    report.py                post-roast: overlay actual vs target, deviation score, updated advice
    calibrate.py             (later) fit causal thermal model from calibration roasts
    live.py                  (later) real-time advisor fed by serial/Artisan WebSocket
  plans/                     generated cue cards + target curves (json + txt + png)
  reports/                   per-roast post-mortem plots
```

## Structured dataset design

**`roasts` table** (one row per roast, keyed by `roastUUID`):
file path, date, title, beans, weight_in/out + unit, ambient temp/humidity, machine tag
(sr800 / yoshan), probe-cohort tag, charge/DRY/FCs/FCe/DROP times and BTs, total time,
development ratio, sampling interval, exclude flag + reason.

**`samples` table** (long format, one row per 2s sample):
roastUUID, t (s from charge), BT, ET, RoR (computed, ~±15s window regression),
fan, power (forward-filled from events), phase (drying/maillard/development).

**Events** can be derived from `samples` transitions or kept as a third small table —
keep a third `events` table (roastUUID, t, type, value) since exact operator action
timestamps matter for lag analysis.

Ingest must be **idempotent** (re-running over the full archive upserts by roastUUID,
never duplicates) so the user can drop new `.alog` files into `data/raw/` after every
roast session and re-run `ingest.py`.

## Processing the larger archive

The user has a much larger `.alog` collection. First run:

1. `ingest.py --scan <folder>`: parse everything; report per-file: parsed OK / missing
   CHARGE / missing DROP / no events / suspected probe cohort.
2. Cluster roasts by FCs BT and curve shape to detect probe/config cohorts; present the
   clusters to the user to label (keep / exclude / separate cohort).
3. Only cohort-consistent roasts feed the planner by default.

## Immediate build order

1. `alog.py` + `ingest.py` + parquet tables; run over full archive; data-quality report.
2. Port `designer.py` + `planner.py` from prototypes onto the dataset; CLI like:
   `plan --tp 140 --fcs 392 --drop 407 --time 9:00 --dev 0.19 [--machine sr800]`
   → cue card txt + png + a target-curve JSON that `report.py` can consume.
   Also export the designed curve as an Artisan background profile (`.alog` with the
   target as temp2) so the user can load it in Artisan while roasting.
3. `report.py`: after a roast, `report --target plans/X.json --roast data/raw/new.alog`
   → overlay plot, deviation stats (max/mean BT error, RoR error by phase, FCs/DROP
   time+temp misses), and suggested plan adjustments.
4. Calibration-roast protocol + `calibrate.py` (constrained fit). Only then attempt
   model-based planning for novel profiles.
5. Yoshan phase: same pipeline, machine tag 'yoshan', single "gas" event slider
   (Config → Events → Sliders in Artisan), expect longer lags; calibration roasts
   required since there is no Yoshan history yet.

## Live architecture decision (v2, after the offline loop works)

No front end, no Artisan fork, **no LLM/API calls at roast time**. The live advisor is a
deterministic local script. Claude's role is between roasts (design, analysis, refinement).

- `bridge.py` owns the serial port (`/dev/cu.SLAB_USBtoUART`, 9600 8N1), decodes the
  Mastech MS6514 stream, and serves readings to Artisan via **Artisan's WebSocket device**
  (Config → Device → WebSocket; Artisan polls with a `getData` command and expects a JSON
  reply with named data nodes). Artisan keeps working as the display/logger.
- The advisor runs inside the bridge: loads target JSON + cue-card plan and prints to the
  terminal. **Terminal only — no voice prompts.** The user runs Artisan on one half of the
  screen, terminal on the other. Each planned change is announced **~10 seconds before**
  it is due (lead time configurable), e.g.:
  `UPCOMING (4:25): Power -> 7` then at the due time `NOW: Power -> 7`.
  A status line refreshes every few seconds:
  `4:30 | BT 338 (tgt 341, -3F) | RoR 24.1 (tgt 26.0) | F8/P7 | ON PLAN`.
  Deviation-triggered recommendations (off-plan corrections) print in the same format,
  visually distinct (e.g. `ADJUST: Power -> 8 (running 6F cold)`).
- Fallback mode if the Artisan WebSocket integration fights back: bridge-only logging with
  its own minimal live plot, exporting an Artisan-compatible `.alog` afterward.

## Bridge verification plan (all stages pass BEFORE any live roast)

The two real risks are the MS6514 protocol decode and Artisan's expected WebSocket JSON.
Both are testable without heat. Core trick: **record once, replay forever.**

**Stage 0 — Capture ground truth.** Close Artisan. Run a raw dump script that reads the
serial port for ~2 min and saves timestamped raw bytes (hex). During capture, the user
writes down the temps shown on the meter LCD (both channels, a few readings with
timestamps). Also capture Artisan's Help → Serial Log output for the same meter for
protocol cross-reference. Deliverable: `tests/fixtures/ms6514_capture_*.bin` + notes.

**Stage 1 — Decoder unit tests.** Parse the captured bytes offline; assert decoded temps
match the LCD notes (±1°F), correct channel assignment, F/C flag handling, and graceful
handling of truncated frames and a disconnected probe. No hardware in the test loop.

**Stage 2 — Fake meter (replay).** A simulator that replays either a byte capture or a
historical `.alog` as a live serial stream (pyserial `loop://` or a pty pair via
`socat`). The bridge must not know it isn't real hardware. This enables full end-to-end
tests of an entire 10-minute roast in seconds (accelerated clock) or real time.

**Stage 3 — Artisan integration against the fake meter.** Point Artisan's WebSocket
device at the bridge while the bridge replays a historical roast in real time. Press ON
and CHARGE in Artisan and let it record. Pass = Artisan's recorded curve overlays the
original `.alog` within interpolation error (automate: export and diff). This proves the
JSON format, node naming, units, and sampling timing with zero risk.

**Stage 4 — Live bench test, no beans.** Real meter, probes at room temp: verify Artisan
display matches the meter LCD. Then 15-minute soak test: no dropped connections, no
sampling gap >5s. Then unplug/replug the USB adapter mid-run: bridge must recover or fail
loudly (no silent stale readings — stale data during a roast is worse than a crash).
Optionally run the empty roaster to see a real thermal curve.

**Stage 5 — Advisor dry run.** Replay a historical roast through the full stack; the
printed recommendations must exactly match the offline `replay` tool's output for the
same roast + target (determinism check), including the 10s-lead announcements.

**Acceptance checklist before first real roast:** decoder matches LCD ±1°F · full-roast
replay renders correctly in Artisan · 15-min soak with zero gaps >5s · unplug test fails
loudly · advisor output identical to offline replay · charge auto-detection fires within
5s of the actual charge on ≥5 replayed historical roasts.
Only after all six: roast cheap beans, follow the advisor, and afterward run `report.py`
as the final validation.

## Roast-day workflow

1. **Warm up** the SR800 as usual (machine preheat; user targets ~300°F chamber reading).
2. **Start the bridge** (`live.py --target plans/X.json`) and **start Artisan** (ON, so it
   is sampling via the bridge's WebSocket feed). Both are running and showing live temps
   *before* any beans go in. Target curve is loaded in Artisan as background profile.
3. **Charge the beans.** The user presses CHARGE in Artisan as usual. The bridge
   **auto-detects charge** from the BT signature (sharp plunge from preheat toward the
   turning point — unmistakable in this data); spacebar in the terminal is the manual
   fallback/override. Auto-detection is required because Artisan's CHARGE button is not
   visible to the bridge. The advisor clock (t=0) starts at detected charge.
4. **Opening block (standard, fixed):** the user's habitual opening is **fan 9 / power 1
   for the first ~60–75 seconds** (gentle bean drying/warm-up). Bake this into every plan
   as a fixed opening — the advisor's first real recommendation comes at the end of this
   block (~1:00–1:15), when the power ramp begins. Historical data below ~200°F is sparse
   and extrapolated anyway, so do not generate kNN recommendations inside the opening
   block; just display the countdown to the first ramp step.
5. **During the roast:** user watches the terminal, applies each recommendation on its
   `NOW` cue (announced 10s early), and logs every fan/power change in Artisan via the
   sliders as usual (Artisan remains the official record of what was actually done).
   User marks FCs/DROP in Artisan as usual.
6. **After the roast:** save the `.alog`, run
   `report.py --target plans/X.json --roast <new.alog>`, review, regenerate plan.

**DRY phase policy:** the user only occasionally logs the DRY mark in Artisan — do not
depend on it anywhere. Compute phase boundaries from BT thresholds instead (drying ends
~300°F, development starts at FCs). Where a manual DRY mark exists, it can be used as a
cross-check but never as a required field.

## Post-roast validation (what `report.py` measures)

Two separate scores per roast — keep them distinct:

1. **Profile adherence (system test): actual curve vs target curve.**
   - Milestones: TP time/temp, FCs time/temp, DROP time/temp vs target (report deltas).
   - DTR achieved vs designed.
   - BT error (mean/max) and RoR error by phase (drying / maillard / development),
     computed from `compare_from_s` onward.
   - RoR shape check: monotonically declining? any crash (RoR < 4 F/min before FCs+30s)
     or flick (RoR rising >2 F/min late)?
2. **Advisor adherence (plan test): actual settings vs recommended settings.**
   - At each recommendation: did the user apply it, how late, or did they deviate?
   - For each deviation: did BT/RoR move closer to or further from target afterward?
     (Deviations that beat the plan are signal — feed them back into the next plan.
      Deviations that hurt confirm the plan.)
   - Recommendation stability: count of direction reversals within 60s (a nervous,
     oscillating advisor is unusable even if "correct" — penalize it).

Output: one PNG overlay (target vs actual BT + RoR, with recommendation and actual-event
markers) and a short text/JSON scorecard per roast, saved to `reports/`.

## Test criteria (user-defined)

Design: preheat 300°F, beans drop to ~140°F TP, FCs ~392°F (decaf, cracks are quiet),
DROP 407°F at 9:00 total, ~19% development. Generate the cue card, roast with it, then
`report.py` scores how close the actual curve came. Success = FCs within ~15s / DROP
within ~3°F and ~15s of target, and the loop produces a better card for attempt 2.

## Notes for Claude Code

- Python 3, numpy/pandas/matplotlib/pyarrow; no heavy ML deps needed yet.
- Never fit on the excluded probe-cohort roasts by default.
- RoR must always be computed from smoothed regression windows (±10–20s), not raw
  2s differences (too noisy).
- Keep `(value-1)*10/11` slider decoding in exactly one place (`alog.py`).
- The user roasts in °F (`mode: 'F'`); support C conversion but don't assume.
