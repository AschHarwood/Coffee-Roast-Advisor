# Roast design reference

Grounded in a ~90-source, evidence-tagged research brief (July 2026); this
file is the operational distillation. Tags: [consensus] = independent
agreement, [contested] = credible authorities disagree.

**Separation of concerns (project policy):** published knowledge decides what
to roast; the user's archive is only the machine model. Absolute temps are
machine-local calibration constants — never copied between rigs.

## Evidence hierarchy — spend design freedom in this order

1. **End color / roast degree** (≈ drop point relative to cracks) — dominant
   flavor driver [consensus, peer-reviewed].
2. **Development time after FC onset** — short = acid/fruit/sweet/clean, long
   = bitter/astringent/roasty/nutty; body unchanged (Münchow 2020, the one
   controlled color-matched study) [consensus]. **Design in absolute dev
   time; DTR is derived display info** (brief §7.2).
3. Everything else (drying length, maillard length, charge temp, RoR
   micro-shape) is practitioner lore or below sensory threshold once color
   and dev time are fixed — don't let it drive the design.

## Roast levels (crack-relative [consensus]; temps = priors to recalibrate)

This rig: FC onset reads ~392–397°F. "Prior here" applies Sweet Maria's
Probat-derived spacing to that anchor; verified range on this rig is only
398–411°F — everything darker is unconfirmed until second crack is actually
observed and logged on this machine.

| Level | Crack-relative definition | Offset | Prior here |
|---|---|---|---|
| Half City | dropped during FC, before it completes | FC+0–5°F | ~395–400 |
| City | at last FC sounds or just after | ~FC+13°F | ~405–410 |
| City+ | 10s–1min after last FC pop | ~FC+20°F | ~412–417 |
| Full City | brink of 2nd crack, before first snap | ~FC+26°F | ~418–423 |
| Full City+ | first few snaps of 2C | ~FC+30°F | ~422–427 |
| Vienna/French | rolling 2C and beyond | FC+36°F+ | unknown here |

## Development time by level × brew (brief §8 table)

| Level × brew | Dev after FC | DTR ref | Drop RoR |
|---|---|---|---|
| Nordic-light / filter | 1:00–1:45 | 13–18% | 6–10 |
| City / filter (house default) | 1:15–2:00 | 15–20% | 5–10 |
| City+ / filter | 1:30–2:30 | 17–22% | 5–8 |
| City+ / espresso (classic) | 2:00–3:00 | 20–25% | 4–7 |
| Full City / espresso or press | 2:15–3:15 | 20–25% | 4–6 |
| Full City+ / press | 2:30–3:30 | 22–25% | ~4–5 |

SR800 note: bias DTR toward the LOW end of each band (Rao's own small-batch /
high burner-to-batch exception targets ~15%). Total time envelope 8–12 min,
FC typically ~5:30–6:30 at 200–225g.

## Bean-class modifiers (applied on top)

| Class | Charge/preheat | Pre-FC | At FC | Development |
|---|---|---|---|---|
| Washed dense (SHB, >680 g/L) | baseline / +10°F | can push early | normal | per table |
| Natural / honey | −10–20°F | gentler (scorch-prone) | normal | per table |
| **Decaf (any method)** | **−10–15°F** | **gentler drying** | **cut heat ~10°F before expected FC — it accelerates after** | **by absolute time; total ~0.5–1 min shorter** |
| Aged / past-crop | −10°F | less energy | normal | per table |

**Decaf control rules [consensus]:** crack may be quiet (roast by temp + time
+ smell); whole-bean color is broken (ground color only); weight loss reads
2–3 pts lower; do NOT roast darker by default — that's a myth specialists
reject. Decaf FC temp direction is contested — calibrate per lot.

## Brew method

Classic school: espresso = one level darker + upper development band
(under-development reads sour under pressure); filter = City–City+, middle
band; french press = Full City ±, upper band. **Modern-light-espresso toggle**
[contested]: with good grinders, filter-style light roasts work as espresso —
if the user identifies with that style, drop the espresso offset. Ask once.

## Open questions → present as user choices (brief §7)

- Smooth-RoR-through-FC enforcement: default ON, label it "Rao doctrine,
  contested" — the peer-reviewed view is it may not matter at matched color.
- DTR ratio vs absolute dev time: we design in absolute time (decided).
- Espresso offset: classic vs modern-light (toggle above).
- Decaf FC temp direction: learn per lot from their logs.

## Hard constraints

Enforced in code — `designer.validate_target()` rejects: stalls (RoR ≤ 0),
sustained near-stall before FC (< 2.5°F/min for > 60s), under-development
(< 60s or < 8% of total), and warns on drop RoR < 4. Don't hand a plan to the
user if validation failed.

## SR800 machine notes [community consensus]

- Fan is a HEAT lever: lowering fan traps hot air and raises BT/RoR. Sweet
  Maria's doctrine is heat high (7–9), profile with fan. (The kNN clones the
  user's own power-ramp style — both work; know which frame you're in when
  explaining.)
- Small batches roast SLOWER (less mass trapping heat) and can stall pre-FC.
- No drum mass: expect to carry/raise heat input approaching FC or the RoR
  crashes (air-roaster adaptation of Rao).
- True "baking" is hard to achieve in a FreshRoast (SM) — don't over-warn.
