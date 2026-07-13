# Tasting analysis — first advised roast (Ethiopia, tasted as espresso)

*2026-07-13, ~12h post-roast. Roast: `first_roast.alog`, scored in
`reports/first_roast_vs_city_10min_dtr22` (FCs +4s, DROP +2s, DTR 21.6%).*

## Observation

Finish very bitter as espresso. This Ethiopia normally shows a sweet, round
finish.

## Diagnosis (ranked)

1. **Rest — the prime suspect.** 12h is far too fresh for espresso: CO₂
   causes channeling and uneven extraction, reading as harsh/bitter finish.
   Standard espresso rest is 5–14 days (decaf opens earlier, ~day 3–4, since
   porous decaf degasses faster — lore, not brief-verified). The remembered
   "sweet round finish" was rested coffee.
2. **Not over-roasting.** Data check: this roast developed 130s and dropped
   +13°F past FC — *shorter and lighter* than nearly every past Ethiopia in
   the archive (those ran 150–250s dev, +15–30°F past FC). If bitterness came
   from roast level, this roast points the wrong way for that theory.
3. **Minor suspects:** the scorecard's late-RoR flick + finishing 4–5°F hot
   (410 vs 406 target) — Rao would call that "roasty" but the claim is
   contested; and grind not re-dialed for a new, ultra-fresh roast.

**Action: re-taste day 4–6 before changing anything.** If still bitter after
rest → address the flick (v2 advisor already cues `Power -> 7` at 7:10 and
`DROP NOW` at 406 on replay of this roast).

## Theory Q&A from this session

**Was this a short roast?** No — FC 7:52 / total 10:02 is exactly the archive
median (FC 7.9m, total 9.9m). By SR800 community standards (SM: FC ~6:00) the
whole archive roasts *slow*. What differed from the sweet-cup memories was
development time (130s vs 150–250s), not total time.

**Are roast level and roast speed independent?** Essentially yes: level =
where you stop relative to the cracks; speed = how fast you traveled. A fast
city and a slow city are both designable. Coupling only at extremes: too fast
= scorch + underdeveloped interior; too slow = pre-FC stall / baked
[consensus] (though true baking is hard on a FreshRoast — SM).

**Fast vs slow to FC at matched level/dev:** real but secondary. Fast retains
acids/volatiles → brighter, more aromatic; slow spends longer in browning →
rounder, deeper, muted acidity (Baggenstoss 2008 [consensus chemistry];
Münchow says pre-FC ≈ ~5% of modulation [contested]). Matters most at very
light levels, gets masked at darker ones.

**Planned experiment (after rest verdict):** matched pair, only total time
moved — same drop 406, same dev 105s:
`design --name city_eth_fast --total 540 --dev 105` (FC ~7:15) vs
`--name city_eth_slow --total 690 --dev 105` (FC ~9:45). Rest 5 days, taste
blind.

## Decaf: preserving character/dynamism (recommendations)

Character lives in the two proven levers: **light level + short development**.

1. Never "roast decaf darker" — specialist-rejected myth [consensus]. Target
   city (~405–408 drop on this rig); judge by temp, never bean color.
2. Development 1:20–1:45 for max character (archive habit was 150–250s — the
   biggest change). Espresso compromise: keep level light, dev mid-band ~1:45.
3. Guard post-FC acceleration — decaf runs away after FC [consensus] and
   quietly converts city → city+, eating brightness. Cut heat ~10°F before
   expected FC (~385 here); obey `DROP NOW`.
4. Gentle start, decisive middle: total ~9:00–9:30 so FC lands ~7:00–7:15.

Candidate next design:
`uv run design --name decaf_bright --total 570 --dev 105 --drop-bt 406`

## Open follow-ups

- [ ] Day 4–6 re-taste of first_roast → log verdict here
- [ ] Fast/slow matched-pair experiment
- [ ] `decaf_bright` profile once rest verdict is in
