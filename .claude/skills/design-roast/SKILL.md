---
name: design-roast
description: Roast-design consultation for the SR800 roast advisor - helps choose a roast level (half city / city / city+ / full city / dark), walks through trade-offs (ramp, total time, finish temp, brew method), optionally researches the specific bean (origin/process) on the web, then designs target profiles and cue cards from the user's roast history. Use when the user wants to design a roast, plan a profile for a new bean, asks about roast levels or espresso-vs-drip roasting, or says "let's design a roast".
---

# Design a Roast

A consultation, not a form. Three entry modes — pick by what the user gives you:

- **Quick**: they state constraints → skip to Design.
- **Consult**: they name a style or brew method ("full city for espresso") →
  use [REFERENCE.md](REFERENCE.md) to translate into constraints, showing the
  trade-offs as you go.
- **Research**: they name a bean (origin, process, varietal, decaf?) → web
  research first, then propose 2–3 candidate profiles to test.

## Consult mode

Interview briefly: roast level (or let them describe the cup they want), brew
method (drip / espresso / french press), bean type (decaf?). Translate to
constraints with the tables in [REFERENCE.md](REFERENCE.md) — **all temps in
this rig's BT frame** (its FCs reads ~392–397°F; published numbers must be
translated, never copied). Explain each trade-off in one sentence as you set
it: total time (body vs baked risk), DTR/finish temp (sweetness vs roast
character), ramp (see reference).

## Research mode

1. WebSearch the bean: `<origin> <process> roast profile`, plus supplier pages
   (Sweet Maria's, Happy Mule, Burman) which publish roast recommendations.
2. Extract: recommended level range, first-crack behavior, density/altitude
   hints, any "shines as espresso/drip" notes. Decaf: see REFERENCE.md — the
   process changes everything (color, crack audibility, speed).
3. Propose 2–3 profiles as a compact table (name, level, total, DTR, drop BT,
   expected cup) and let the user pick which to design — or design all for
   A/B testing across roast sessions.

## Design (all modes end here)

```bash
uv run design --name <name> --total <s> --dtr <x> --fcs-bt <F> --drop-bt <F>
uv run plan --target plans/target_<name>.json
```

Design uses the history-median RoR shape by default (`--shape linear` only for
comparisons). If parquet is missing: `uv run ingest` first.

Sanity checks before handing over:
- Cue card has no dial reversals; kNN support printed by `plan` is healthy.
- **Novelty warning**: history is 9–12 min roasts dropping 398–411°F. For
  darker/faster/longer profiles than that, say plainly that the settings plan
  is extrapolating and the advisor's live corrections matter more than the
  card. Suggest cheap beans for the first attempt.
- Send cue card text + `plans/<name>_plan.png` (SendUserFile, render).

## Hand-off

Roast-day: `uv run live --target plans/target_<name>.json`, Artisan ON
(WebSocket mode per ARTISAN_SETTINGS.md), START during preheat; charge
auto-detects; follow UPCOMING/NOW/ADJUST/DROP cues; mark FCs + DROP.
After: `uv run report --target ... --roast <file>`, review, copy the .alog
into `data/raw/training_data/`, `uv run ingest`. Log tasting notes when the
user shares them — they steer the next design.
