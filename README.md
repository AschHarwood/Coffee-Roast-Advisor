# Coffee Roast Advisor

Data-driven coffee roasting for home roasters who log with
[Artisan](https://artisan-scope.org/). It learns how *your* machine responds
to *your* dial changes from your own roast history, then:

1. **Designs** a target roast curve from constraints (total time, development
   ratio, first-crack temp, drop temp) — using the RoR shape your machine
   actually produces, measured from your logs.
2. **Plans** a cue card: timestamped fan/power settings predicted from what
   you did in every similar moment of your roasting history (kNN over
   bean-temp/RoR states).
3. **Advises live** during the roast: a terminal bridge that reads your
   thermocouple, feeds Artisan over WebSocket, auto-detects the charge, and
   calls out each change 10 seconds early — plus corrections when you drift
   and a drop-window warning.
4. **Scores** the finished roast against the target (milestones, DTR, phase
   errors) *and* against the plan (did deviations help?), then ingests it so
   the next plan is smarter.

Status: working end-to-end on a Fresh Roast SR800 (fluid bed, Mastech MS6514
thermocouple). First advised roast landed first crack +4s and drop +2s from
the designed target. 107 tests run against the real included data.

## Quick start

Requires [uv](https://docs.astral.sh/uv/). Clone, then:

```bash
uv sync
uv run ingest                                        # parse the included archive -> parquet + quality report
uv run plan --target plans/target_city_10min_v2.json # cue card from the roast history
uv run design --name my_roast --total 570 --dtr 0.20 # design your own target
uv run report --target plans/target_city_10min_v2.json --roast <your.alog>
```

Everything works offline from `.alog` files — no hardware needed until you
want the live advisor.

## The live bridge (optional, roast-time)

`uv run live --target plans/<target>.json` owns the meter's serial port,
serves temps to Artisan (Config → Device → WebSocket; see
[ARTISAN_SETTINGS.md](ARTISAN_SETTINGS.md)), and prints the advisor cues.
Supporting tools, built so every layer is testable without heat:

- `uv run capture` — record raw meter bytes for decoder verification
- `uv run fakemeter --alog <file>` — replay any historical roast as a fake
  serial meter (the bridge can't tell the difference)
- `uv run replay --target <json> --roast <alog>` — offline advisor transcript;
  the live stack must produce identical output (tested)

Currently supports the Mastech MS6514 protocol; the decoder is one small
module ([src/roast_advisor/ms6514.py](src/roast_advisor/ms6514.py)) — PRs for
other meters welcome.

## Claude Code integration

The repo ships a [Claude Code](https://claude.com/claude-code) skill:
open the repo in Claude Code and say **"/design-roast"** (or "design me a
full city for espresso") for a guided consultation — roast level trade-offs,
bean research (origin/process → suggested profiles), then automatic target +
cue-card generation. The core CLI needs no AI; the skill adds the
consultation layer. A standalone app (no Claude Code required) is on the
roadmap.

## Contributing training data 🙏

The model gets better with more logged roasts, and probe frames differ across
rigs — data from your machine helps everyone with that machine class.

**What to send:** raw Artisan `.alog` files, plus (in the PR/issue text) your
machine model, heat type, and roughly where your probe reads first crack.

**How:** open a PR adding files under `data/raw/community/<your-handle>/`, or
just attach them to an issue. Ingest dedupes by `roastUUID`, flags probe
cohorts automatically (roasts whose first-crack temp is >30°F off cohort
median are excluded from modeling until labeled), and never mixes cohorts
silently. Decaf roasts especially welcome — the current archive is decaf-heavy
and we'd like both.

Also valuable: fan/power (or gas) event logs on *any* small roaster. Gas drum
roasters (Yoshan, Huky, Mill City, ...) all reduce to the same schema — one
continuous burner value logged as Artisan events — and are the next machine
class we want to support.

## How it works (architecture)

| Module | Role |
|---|---|
| `src/roast_advisor/alog.py` | single source of truth for `.alog` parsing, dial decoding, charge detection, RoR |
| `ingest.py` | idempotent archive → parquet (roasts / samples / events) + data-quality report |
| `dataset.py` | cohort filtering, kNN training matrix, measured machine RoR shape |
| `designer.py` | constraints → target BT/RoR curve (machine-shape or linear) |
| `planner.py` | target + history → cue card (weighted kNN, dial smoothing, deadband) |
| `report.py` | post-roast scoring: profile adherence + advisor adherence |
| `ms6514.py`, `capture.py`, `fakemeter.py`, `live.py` | the hardware bridge stack |

Design principles:

- **Published roasting knowledge decides what to roast; your data only models
  how your machine gets there.** Temps are treated as rig-relative (anchored
  to your measured first crack), never copied across probes.
- **Deterministic at roast time.** The live advisor is plain math over
  pre-computed plans — no model calls, no network, reproducible transcripts.
- **Behavior cloning over physics.** A pooled thermal model is unidentifiable
  on consistent home-roast history (power correlates with bean temp); kNN
  over demonstrated behavior is honest and degrades gracefully. See
  [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) for the full reasoning.

## Tests

```bash
uv run pytest
```

Tests run against the real archive: decoding against LCD-verified serial
captures, idempotent ingest, leave-one-out replay (plans must match the
operator's actual historical settings within ±1 dial at most checkpoints),
charge detection within 5s, and live-vs-offline advisor determinism.

## Roadmap

- Ground the curve designer in published roast science (research brief in
  [RESEARCH_PROMPT.md](RESEARCH_PROMPT.md))
- Community `.alog` corpus with per-rig normalization ([DATA_HUNT_PROMPT.md](DATA_HUNT_PROMPT.md))
- Gas drum support (Yoshan 2kg first): calibration-roast protocol, single
  "gas" control axis, longer thermal lags
- Causal thermal model from deliberate calibration roasts (enables novel
  profiles beyond the history)
- Standalone app — no Claude Code dependency

## License

AGPL-3.0 — see [LICENSE](LICENSE).
