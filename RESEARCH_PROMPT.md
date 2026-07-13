# Prompt for deep-research app (copy everything below the line)

---

I need a research brief on coffee roast design — the science and the accumulated
professional/community knowledge — that will be encoded into software. The
software designs target roast curves (bean temperature over time and its
rate-of-rise) for a home fluid-bed roaster (Fresh Roast SR800, ~200g batches),
and later a 2kg gas drum roaster. It already knows HOW to hit a target curve on
the specific machine; what it needs from you is authoritative knowledge about
WHAT curve to target and why. Research the following and produce the brief
described at the end.

## Research questions

1. **Roast curve science (Rao and beyond).** Scott Rao's prescriptions:
   continuously declining rate-of-rise (RoR), no crash or flick, development
   time ratio (DTR) 20–25%, drying/maillard/development phase framing. What is
   the actual evidence for these? What do credible critics say (e.g., roasters
   who intentionally use non-declining RoR, shorter DTR Nordic styles)? Where
   is the genuine consensus vs. Rao-specific doctrine?

2. **Roast level definitions.** How do professionals define half city / city /
   city+ / full city / Vienna / French? Confirm: are levels defined by crack
   events and bean color (Agtron), by drop temperature, or by time after first
   crack? How much do absolute bean-temp readings vary between machines and
   probe placements (i.e., why copying another rig's drop temp is unreliable)?
   Express any temperature guidance RELATIVE to first crack onset, not
   absolute.

3. **Curve → cup: what actually changes flavor.** For each lever, what does
   published knowledge say about flavor impact: total roast time (fast vs slow),
   drying-phase length, maillard-phase length, DTR / development time, drop
   temperature / final level, RoR at drop, charge temperature. Distinguish
   controlled-experiment evidence (e.g., published cupping studies, Coffee Mind /
   SCA research) from practitioner lore.

4. **Bean-driven adjustments.** How should origin, process (washed / natural /
   honey), density / altitude (SHB, grown >1500m), screen size, varietal, and
   age change the roast approach? Specifically for DECAF (Swiss Water, CO2,
   ethyl acetate): how does decaffeination change roast behavior (color
   progression, crack audibility, heat sensitivity, recommended level offsets)?
   Most of this software's use is decaf.

5. **Fluid-bed vs drum.** Which of the above transfers to a small fluid-bed
   air roaster and which is drum-specific? Convective-vs-conductive heat,
   typical time compression, probe-reading differences, whether Rao's RoR
   rules were formulated for drums and how air-roaster experts (e.g., the
   Sweet Maria's / Homeroasters / r/roasting SR800 communities) adapt them.

6. **Brew-method targets.** Espresso vs filter/pourover vs french press: what
   development level, DTR, and drop-RoR do professionals recommend and why
   (solubility, acidity under pressure)? Note where sources disagree.

## Output format (strict)

A markdown brief, roughly 3–6 pages, with:

- **Claims tagged by evidence strength**: [consensus] / [contested] /
  [single-source]. Every claim cited inline.
- **Machine-independent vs drum-specific** knowledge clearly separated.
- All temperature guidance expressed **relative to first-crack onset** (e.g.
  "FC + 15–20°F"), with a note on absolute-temp unreliability across rigs.
- A final section titled **"Rules a curve designer can encode"**: a compact
  table of parameter ranges — for each (roast level × brew method × bean
  class): DTR range, total-time range, drop point relative to FC, drop-RoR
  range, and any RoR-shape guidance — plus a short list of hard constraints
  (things a designed curve must never do) and soft preferences, each with its
  evidence tag.
- An **annotated source list**: for each source, one line on who/what it is
  and why it's credible (books, SCA/Coffee Mind research, established roaster
  blogs, supplier education pages like Sweet Maria's, active community threads
  for SR800-specific behavior).

Flag open questions where the internet genuinely disagrees rather than
smoothing them over — disagreements will be surfaced to the user as choices,
not hidden.
