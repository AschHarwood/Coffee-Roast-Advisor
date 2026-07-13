# Roast design reference

**Separation of concerns (project policy):** roast-level definitions, target
temps, and trade-offs come from PUBLISHED professional guidance (research mode
is the primary source, fetched fresh per bean). The user's roast archive is
used ONLY as the machine model — how settings move temperature on this rig —
never as the standard for what a good roast is.

## Roast levels — define by crack events, not copied temps

Professional sources define level by where the drop lands relative to the
cracks (which tracks bean color/chemistry). Dev time/DTR tunes flavor balance
WITHIN a level; "time after FC" alone is a poor level proxy because post-FC
RoR varies with power.

| Level | Event definition | DTR guide |
|---|---|---|
| Half city (city−) | FC start heard, dropped before FC finishes | 8–14% |
| City | shortly after FC ends | 15–20% |
| City+ | past FC, well before any SC sign | 20–24% |
| Full city | at the first hints/verge of second crack | 22–26% |
| Dark / french | into rolling SC | 25%+ |

**Translating to this rig's temps:** FCs reads ~392–397°F here. The archive
verifies the region 398–411°F (city / city+ territory) — that is the ONLY
temp range this probe has ever confirmed. Second crack has never been recorded
on this rig, so full-city+ drop temps are unknown in this frame: published
"SC ≈ 435–445°F" numbers come from other probes and must not be copied.
For darker targets: research the bean, set a provisional drop temp a few °F
past the verified range, and roast by ear (SC) with the live advisor — then
the recorded roast calibrates the frame for next time.

## Brew method

| Brew | Lean toward | Why |
|---|---|---|
| Drip / pourover | city – city+ | acidity reads as flavor clarity in filter |
| Espresso | city+ – full city, DTR 22–26%, drop RoR ~4–5 | pressure amplifies acidity; more development = balanced shots; underdeveloped espresso is sour |
| French press / cold brew | full city | body carries; brightness is muted anyway |

## Trade-offs to narrate while setting constraints

- **Total time**: shorter (≤9 min) = brighter, lighter body, riskier control;
  longer (≥11 min) = heavier body but baked/flat risk if RoR stalls. History
  sweet spot: 9:30–10:30.
- **DTR / finish**: raising drop temp at fixed time deepens roast character;
  raising DTR at fixed drop temp trades acidity for sweetness/roundness.
- **Ramp**: the machine's RoR shape is measured from history (rebound spike →
  steep decay) — the designer handles it. The lever the user actually chooses
  is total time + FCs timing, not the ramp shape itself.
- **Drop RoR**: 5 F/min default; pushing below ~4 flattens the cup (Rao floor),
  above ~7 risks the late flick and overshooting the drop temp.

## Decaf notes (most of this history is decaf)

- Process (SWP/MC) pre-browns the bean: color is useless for judging level —
  go by temp and time only.
- First crack is quiet or inaudible: user assumes FCs at ~395 on this rig and
  marks it manually; treat the FCs mark as ±30s soft.
- Decafs run ~faster and roast darker at the same BT: when a supplier
  recommendation is for the non-decaf version, ease the drop temp down ~2–4°F.

## Research playbook

Search patterns: `<origin> <region> <process> roast profile`,
`<bean name> sweet marias`, `roasting <origin> decaf`. Supplier product pages
(Sweet Maria's, Happy Mule, Burman, Genuine Origin) publish roast level
recommendations and cupping notes — the most actionable sources.

Translate supplier language: "City+ recommended" → the table above; "shines
darker" → full city candidate; "delicate florals" → half city/city candidate;
dense high-grown (SHB/SHG, >1500m) tolerates faster ramps and darker levels;
low-grown/aged/monsooned beans prefer gentler, shorter roasts.

Deliverable: 2–3 named candidates spanning the plausible range, e.g.
`ethiopia_city_945`, `ethiopia_cityplus_1030` — design all, A/B across
sessions, and let `report` + tasting notes pick the winner.
