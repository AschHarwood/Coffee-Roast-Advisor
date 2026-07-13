# Roast Curve Design: Science & Professional Knowledge Brief

*Research brief for encoding into roast-curve-design software. Target machines: Fresh Roast SR800 fluid-bed (~200g), later a 2kg gas drum. Compiled July 2026 from ~90 sources across five research threads; every claim tagged [consensus] / [contested] / [single-source].*

**How to read this:** [consensus] = independent agreement across credible sources with no serious dissent. [contested] = credible authorities actively disagree — surfaced in §8 as user choices. [single-source] = one credible source, unverified elsewhere. Knowledge marked **(drum)** does not transfer to fluid-bed without re-derivation; unmarked knowledge is machine-independent.

**Temperature convention:** all guidance is expressed relative to first-crack onset ("FC+X°F") or to crack events/time, never absolute. Reason: the *same physical event* reads wildly differently across rigs — documented FC-onset readings span ~330°F to ~410°F displayed depending on probe diameter, placement, batch size, and machine ([Home-Barista](https://www.home-barista.com/roasting/first-crack-fc-temperature-at-332f-t39472.html), [Roast World](https://community.roast.world/t/typical-temps-for-cracks-and-delta-between-them/2715), [Sweet Maria's](https://library.sweetmarias.com/first-crack-faq-what-is-first-crack-what-is-second-crack/)). A thick vs thin thermocouple alone shifts end-of-roast readings 13°F on the same batch ([Barista Hustle, citing Hoos 2017](https://www.baristahustle.com/lesson/rs-4-08-probe-size-and-placement/)) [consensus]. The stock SR800's display reads inlet air, not bean mass, and can run 80–100°F above actual bean temp ([Tom's Coffee Pages](http://cholla.mmto.org/coffee/sr800/notes_2025.html)) [single-source magnitude, consensus direction]. **Encodable rule: absolute temps are machine-local calibration constants, learned per rig+probe from logged FC events; never copied between rigs.**

---

## 1. Roast curve science: Rao's doctrine vs the evidence

Scott Rao's prescriptions ([Coffee Roaster's Companion, 2014; blog](https://www.scottrao.com/blog/2016/8/25/development-time-ratio)): bean-temp rate-of-rise (RoR) should decline continuously from turning point to drop; avoid the "crash" (sharp RoR drop at first crack, which he says causes *baked* flavor) and the "flick" (late RoR rise, causing *roasty* flavor); development time ratio (DTR = time from FC to drop ÷ total time) of 20–25%.

**What his evidence actually is:** cupping correlation, self-reported — "18 of the best 20" of ~20,000 tasted roasts fell at 20–25% DTR, which he himself calls "not proof of anything" [contested]. His crash→baked claim rests on uncontrolled practitioner observation with no blinded protocol ([What is Baked Coffee, 2018](https://www.scottrao.com/blog/2018/2/24/what-is-baked-coffee-most-pros-dont-know)) [contested].

**The strongest counter-evidence** is the one peer-reviewed controlled study in this space: Münchow et al., *Beverages* 2020 ([MDPI, open access](https://www.mdpi.com/2306-5710/6/4/70)). At identical roast color (Agtron 76±1) and identical time-to-FC, **shorter development time gave significantly more acidity, fruit, sweetness, and clean cup; longer development gave more astringency, bitterness, nutty/chocolate, roasted notes** — p<0.001 on every descriptor except body, which did not change [consensus on direction]. Companion multi-study analysis ([Beverages 2020, 6(2):29](https://www.mdpi.com/2306-5710/6/2/29)): **roast color is the dominant flavor driver** (Münchow's heuristic: ~80% color, ~15% development time, ~5% pre-FC timing) [contested on exact split].

**Münchow's methodological attack** ([CoffeeMind](https://coffee-mind.com/why-rate-of-rise-is-a-bad-reference-point/)): a declining RoR is largely the *natural thermodynamic default* (heat transfer shrinks as bean temp approaches environment temp); small RoR wiggles are below sensory threshold once color and development time are matched; and the crash-vs-smooth claim is untestable as posed because you cannot vary RoR shape while holding color and development constant [contested — Kornman of Royal Coffee rebuts that real roasters don't run constant heat and RoR is a legitimate predictive "speedometer" ([Royal Coffee, 2023](https://royalcoffee.com/rate-of-rise-where-do-you-stand/))].

**Rob Hoos' middle position** (*Modulating the Flavor Profile of Coffee*, 2015): the crash is mostly a measurement artifact (cool moisture released at FC hits the probe — a mechanism Rao himself acknowledges) [consensus on mechanism, contested on flavor impact]; flavor is steered by modulating *phase durations*, not by policing curve shape [single-source framework, widely respected].

**Where genuine consensus exists** (safe to hard-code): RoR is heavily probe-dependent and noisy; RoR is useful as a *predictive/waypointing* tool; development time is a real flavor lever (short=bright/fruity, long=roasty/bittersweet — the peer-reviewed result); end color/degree dominates flavor; gross stalling (flat-to-zero RoR dragging on pre-FC) and scorching are defects; plan the roast rather than improvising large late corrections.

**Rao-specific doctrine** (encode as *defaults with an off-switch*, not laws): continuous decline as a quality requirement; crash as the primary cause of baked flavor; the specific 20–25% DTR window; flick as independently harmful at matched color.

---

## 2. Roast level definitions

Names have never had universal specification ([Mill47](https://mill47.coffee/blogs/take2/guide-to-city-roast-levels), [Coffee Review](https://www.coffeereview.com/roast-definitions/)) [consensus]. The only near-consensus definitional layer is **crack-relative events**; Agtron ground color is the measurement ground truth; drop temperature is machine-local. Sweet Maria's (the home-roasting authority, including for air roasters) provides both crack-relative definitions and their own Probat-measured temps ([roast level glossary](https://library.sweetmarias.com/glossary/city-roast/), [color card](https://library.sweetmarias.com/sweet-marias-roasted-coffee-color-card/)).

| Level | Crack-relative definition [consensus] | Rel. temp (SM Probat: FC onset ≈ 412°F) | Agtron (ground, approx) [contested] |
|---|---|---|---|
| Half City / Cinnamon | Stopped during FC, before it completes | ~FC+0–5°F | 85–95 |
| City | Drop at last sounds of FC or just after; no push toward 2C | ~FC+13°F | 65–75 |
| City+ | 10s–1min after last FC pop (≈FC end + 30s) | ~FC+20°F | ~60 |
| Full City | Brink of 2nd crack, before first snap | ~FC+26°F | 50–60 |
| Full City+ | First few snaps / ~10s of 2C | ~FC+30°F | 45–50 |
| Vienna | 2C rolling | ~FC+36–53°F | 35–45 |
| French | Toward end of 2C, surface oils | ~FC+36°F (SM card) to +60°F (other SM pages) | 25–35 |

Notes: the relative-°F column is derived from one rig (Sweet Maria's Probat L12) and is itself only a starting prior — even SM says the Aillio Bullet "runs about 20°F behind this chart" [consensus on unreliability]. Agtron-to-name mappings disagree across sources (Mill47's tidy 70/60/50/40 vs others) [contested]. Weight loss (~10% at FC → ~15% at FC+) is a useful within-machine cross-check but not portable across machines [consensus as local tool]. Decaf breaks whole-bean color entirely (§4).

**Encodable rule:** define levels by (a) time/temp offset from *detected FC onset*, learned per rig, and (b) verify by ground color / weight-loss trend per machine. Never encode absolute drop temps as level definitions.

---

## 3. Curve → cup: what each lever does, by evidence quality

**Real experimental support (controlled, color-matched):**

- **Development time (FC→drop)** — the flagship lever. Short = acidity/fruit/sweetness/clean; long = bitter/astringent/roasty/nutty. Body unchanged ([Münchow, Beverages 2020](https://www.mdpi.com/2306-5710/6/4/70)) [consensus].
- **Roast degree / end color** — dominant driver; darker = more bitter, less acid/fruit/sweet ([multi-study](https://www.mdpi.com/2306-5710/6/2/29), [SCA](https://sca.coffee/sca-news/coffee-decoded-3-roast-level-consumers)) [consensus].
- **Overall fast-vs-slow to matched color** — different aroma-compound kinetics (HTST vs LTLT, [Baggenstoss et al. 2008, J. Agric. Food Chem.](https://pubmed.ncbi.nlm.nih.gov/18572953/)) [consensus chemistry, preference verdict open].

**Practitioner authority only (plausible, not isolated experimentally):**

- **Maillard-phase length** → body/syrupy/chocolate depth (Hoos) [contested — the controlled study found body didn't move with timing; no clean Maillard-only experiment exists].
- **Crash/flick → baked/roasty** (Rao) [contested, see §1].
- **DTR 20–25%** (Rao) [contested; CoffeeMind's data suggests *absolute development time* + color carry the information, the ratio per se is derivative].
- **RoR at drop high = juicy, low = baked** [contested/lore — folds into the crash debate].

**Mostly lore / confounded:**

- **Drying-phase length as independent lever** — notably, *both camps downplay it* (Rao: over-weighted label; Münchow: pre-FC ≈ 5% of modulation) [consensus that it matters less than forums think].
- **Charge temperature as flavor knob** — matters via defects (scorching/tipping) and roast speed, not independently ([MTPak](https://mtpak.coffee/2021/11/coffee-roasting-controlling-charge-temperature/)) [consensus operational view].
- **Airflow → "juiciness"** — one sharp Feran anecdote ([Roest best practices](https://christopherferan.com/2023/12/30/roest-best-practices/)) [single-source].

**Encodable hierarchy:** end color (≈ drop point) ≫ development time ≫ everything else. A curve designer should spend its degrees of freedom in that order.

---

## 4. Bean-driven adjustments

**General** (direction [consensus], magnitudes mostly [single-source]):

- **Process:** naturals/honeys charge lower and take gentler early heat (residual sugars scorch; one roaster: ~30% lower charge for a soft natural vs dense washed [single-source]) ([PDG](https://perfectdailygrind.com/2017/10/how-to-roast-natural-honey-processed-coffee/)).
- **Density/altitude:** dense high-grown (>~1500m, >~680 g/L) tolerates/benefits from more early energy; ~40–50 g/L density difference ≈ 10–15°F charge adjustment [single-source figures] ([ICT](https://www.ictcoffee.com/news/managing-charge-temperature-for-different-densities/)). Measure density; don't trust SHB labels ([Roast Magazine](https://www.roastmagazine.com/stories/beyond-elevation)) [consensus].
- **Screen size:** small screens/peaberries absorb heat faster, roast faster; mixed screens smear first crack [consensus].
- **Age:** past-crop = drier = needs less energy, lower charge ([Royal NY](https://www.royalny.com/blogs/green-coffee-aging-roasting-profiles/)) [consensus].

**DECAF (primary use case).** All methods (Swiss Water/CO2/EA) rehydrate and re-dry the bean, weakening cell structure [consensus]:

- **Visual cues are broken:** greens are brown, whole-bean color stays dark and compressed in range (Royal measured whole-bean color range 6.34 vs 12.35 ground across their decaf roasts) — judge by **ground color, temp, time-after-FC, aroma**, never whole-bean color ([Swiss Water](https://www.swisswater.com/blogs/sw/optimizing-the-roast-of-decaffeinated-coffee), [Sweet Maria's](https://library.sweetmarias.com/roasting-decaf-coffee/), [Royal](https://royalcoffee.com/reconsidering-how-we-roast-decaffeinated-coffees/)) [consensus].
- **First crack is quiet** — few, soft pops, sometimes inaudible; roast by temp+time+smell [consensus]. (SM's 2024 update: many current SWP lots do crack audibly — treat silence as possible, not guaranteed.)
- **FC temperature is contested:** SM says decafs can crack lower; the only controlled same-lot study (Al-Shemmeri, EA decaf, [Medium](https://medium.com/@markalshemmeri/the-effect-of-decaffeination-on-coffees-roasting-and-grinding-performance-229ea8450e46)) found decaf cracked *higher* with a smooth, unperturbed RoR through FC [contested — calibrate per lot].
- **Heat handling:** absorbs heat faster; charge ~10–15°F lower with a gentler drying ramp [consensus, exact offset contested]; **post-FC it accelerates — cut heat just before/at FC** or it runs away [consensus]; expect to drop slightly earlier/shorter total time than the equivalent regular coffee [consensus among specialists].
- **Rao's reframe:** weakened cellulose means no violent FC moisture release, so decaf RoR curves are naturally smooth — decafs are *easy* by his rules [contested framing, consistent with Al-Shemmeri's data].
- **Weight loss reads ~2–3 points lower** than regular at the same level (mass already removed) — recalibrate any weight-loss QC [consensus].
- **Level choice:** no credible source supports "always roast decaf darker"; specialists explicitly push back. Expect oil sheen earlier (porous walls) without it meaning "dark" [consensus].

**Encodable rules:** bean-class parameter = {washed, natural/honey, decaf} × density class. Decaf: charge offset −10–15°F, gentler pre-FC ramp, mandatory heat cut at FC−~10°F, development tracked by time-after-FC (not sound, not whole-bean color), expected total time ~0.5–1 min shorter, weight-loss target −2–3 pts.

---

## 5. Fluid-bed vs drum: what transfers

**Machine-independent (safe for both SR800 and future Yoshan):** declining-RoR-as-default-shape; crash/flick *concepts*; DTR as a ratio plus its small-batch exception (below); FC at ~75–80% of total time (Rao's correlational framing); develop light roasts fully; the probe-relativity principle (§0); development-time flavor direction (§3).

**Drum-specific — must be re-derived on the SR800:** every absolute number (charge temp, turn time/temp, peak RoR); the hot drum mass that carries beans through FC's endothermic dip — **on an air roaster you compensate by letting air temp drift up approaching FC** (Rao's own air-roaster adaptation, [home-barista](https://www.home-barista.com/roasting/development-time-as-ratio-roast-time-by-scott-rao-t30830-80.html)) [consensus among Rao-followers]; heat-retention scheduling (drum retains heat late, fluid bed doesn't).

**Rao's rules were formulated on drums** — he states his guidelines assume "a classic drum roaster, charging with >60% of capacity" ([DTR blog](https://www.scottrao.com/blog/2016/8/25/development-time-ratio)) [consensus]. His stated exception is directly relevant: when burner-capacity-to-batch ratio is high (sample roasters, home air roasters), **target DTR drops toward ~15%**.

**SR800-specific community practice** ([Sweet Maria's tip sheet](https://www.sweetmarias.com/media/sebwite/productdownloads/s/r/sr800_tip_sheet_1.pdf), home-barista/Artisan threads) [consensus within this community]:

- Best batch ~215g, max ~225g; landmarks: FC ~6:00, City+ ~8:00, 2C ~10–12:00. Air roasts compress time vs drum [consensus]; SM advises not delaying FC much past ~6 min and notes true "baking" is hard to achieve in a FreshRoast.
- **Fan is a heat lever, not just agitation:** lowering fan traps hot air under the bean mass and *raises* BT/RoR; SM's philosophy is heat high (7–9) throughout, profile primarily with fan, stepping fan down as beans lose density [consensus for this machine]. Fan steps produce jumpy RoR spikes that need feathering [consensus among SR800+Artisan users].
- Small batches paradoxically roast *slower* (less mass trapping heat) and may stall before FC [consensus].
- Fluid-bed cup character "brighter/cleaner, less body" than drum [contested — plausible direction, vendor-inflected].

---

## 6. Brew-method targets

**Classic school** [consensus as the traditional position]: espresso gets more development/darker drop (solubility and body for 9-bar extraction; under-development reads as harsh sourness under pressure); filter roasts lighter/shorter to preserve acidity and clarity ([PDG](https://perfectdailygrind.com/2019/07/roasting-for-filter-coffee-vs-for-espresso/)). Rao's caution: don't just stretch development to mute acidity — it kills sweetness; rebalance the whole profile [consensus among modern roasters]. French press (immersion, full body tolerance): typically City+ to Full City+, body-forward [lore — no rigorous source found].

**The live dissent** [contested]: the modern light-espresso movement holds that with modern grinders, light filter-style roasts extract fine as espresso, and extra development is a stylistic choice, not a requirement ([Pit Stop](https://www.pitstopcoffeeco.com/blog-1/nordic-style-roasting-for-espresso), [Seattle Coffee Gear](https://www.seattlecoffeegear.com/blogs/learning-center/working-with-light-roast-espresso)). Omni-roasting (one profile for both methods) is established practice, implicitly conceding the split isn't mandatory ([PDG omni guide](https://perfectdailygrind.com/2021/08/top-tips-for-omni-roasting-coffee/)).

**Encodable:** brew method shifts the *default* level and development band (espresso: one level darker + upper development band; filter: City–City+ + middle band; french press: Full City ± + upper band) — but expose "modern light espresso" as a user style toggle that removes the espresso offset.

---

## 7. Open questions — surface these as user choices, don't smooth over

1. **Does an RoR crash cause baked flavor, or is it a harmless probe artifact?** Rao: causal. Hoos: artifact, doubtful flavor impact. Münchow: untestable as posed. No color-matched controlled study exists. → *Software choice: "enforce smooth RoR through FC" as a default-on toggle, labeled as Rao doctrine.*
2. **DTR ratio vs absolute development time.** Rao targets the ratio; CoffeeMind's evidence supports absolute time + color as the real levers. → *Software choice: design in absolute development time, display DTR as derived info.* (This brief recommends the latter as primary.)
3. **Espresso development offset** — classic vs modern-light school (§6 toggle).
4. **Decaf FC temperature direction** (lower per SM, higher per the only controlled study) → *learn per lot, don't hard-code.*
5. **Pre-FC phase importance** — Münchow ~5% vs Kornman "decisive for narrow-color light roasting." → matters mainly if the user pushes very light roasts.
6. **Fluid-bed "cleaner cup"** — direction plausible, magnitude unproven; irrelevant to curve design but relevant to expectations when the Yoshan arrives.

---

## 8. Rules a curve designer can encode

**Hard constraints (a designed curve must never):**

- Stall: RoR ≤ 0 at any point between turning point and drop [consensus].
- Prolonged near-stall pre-FC: RoR < ~2–3°F/min sustained >60s before FC onset (bake risk by *everyone's* definition) [consensus].
- Underdevelop: less than ~45–60s or <~8% of total time after FC onset before drop [consensus — even anti-DTR sources agree underdevelopment is the classic light-roast defect].
- Exceed the level definition: BT crossing into rolling 2C when the target level is Full City or lighter [consensus].
- Design in absolute temperatures copied from another machine [consensus].
- (Decaf) rely on crack audibility or whole-bean color as control inputs [consensus].

**Soft preferences (default-on, user-toggleable, tagged):**

- Continuously declining RoR from TP to drop, no sustained rise (flick) [contested — Rao doctrine; harmless to follow, cheap to enforce].
- No sharp RoR slope discontinuity through FC (crash) [contested — Rao doctrine].
- FC onset lands at ~75–80% of total planned time [single-source correlational, Rao].
- RoR at drop ≥ ~4–5°F/min [contested — practitioner lore, anti-"baked" heuristic].
- Plan heat moves early rather than large late corrections [consensus].

**Parameter table** (development time is the primary encoded variable; DTR shown for reference; "rel. FC" = drop offset from detected FC onset on the *local* rig, using SM's Probat-derived spacing as the initial prior to be recalibrated):

| Level × Brew | Dev time after FC onset | DTR (ref) | Drop rel. FC | Drop RoR | Evidence |
|---|---|---|---|---|---|
| City / filter (SR800 default) | 1:15–2:00 | 15–20% | FC+10–15°F | 5–10°F/min | crack-rel [consensus], DTR band [contested] |
| City+ / filter | 1:30–2:30 | 17–22% | FC+18–22°F | 5–8°F/min | same |
| City+ / espresso (classic) | 2:00–3:00 | 20–25% | FC+18–25°F | 4–7°F/min | classic school [contested by light-espresso] |
| Full City / espresso or press | 2:15–3:15 | 20–25% | FC+25–30°F | 4–6°F/min | crack-rel [consensus] |
| Full City+ / press | 2:30–3:30 | 22–25% | FC+30–35°F (first 2C snaps) | ~4–5°F/min | crack-rel [consensus] |
| Nordic-light / filter | 1:00–1:45 | 13–18% | FC+5–12°F | 6–10°F/min | style-specific [contested] |

**Bean-class modifiers (applied on top):**

| Class | Charge/preheat | Pre-FC ramp | At FC | Development | Notes |
|---|---|---|---|---|---|
| Washed, dense (SHB) | baseline / +10°F | can push harder early | normal | per table | density > labels [consensus] |
| Natural / honey | −10–20°F | gentler | normal | per table, watch roasty stack-up | scorch-prone [consensus] |
| **Decaf (any method)** | **−10–15°F** | **gentler, slower drying** | **cut heat ~10°F before expected FC** | **track by time; expect acceleration; total ~0.5–1 min shorter** | quiet FC, ground-color verification, weight loss −2–3 pts [consensus] |
| Aged / past-crop | −10°F | less energy overall | normal | per table | drier bean [consensus] |

**SR800 machine profile:** total time envelope 8–12 min (FC ~5:30–6:30 typical at 200–225g); DTR bias toward the low end of each band (small-batch/high burner:batch exception, Rao) [single-source]; fan is a primary heat lever (down-steps raise RoR) [consensus, community]; expect to raise heat input approaching FC to avoid the crash (no drum mass) [consensus among air-roaster practitioners]; small batches run slower, not faster [consensus].

---

## 9. Annotated sources

**Peer-reviewed / controlled:**
- [Münchow et al., Beverages 2020 6(4):70](https://www.mdpi.com/2306-5710/6/4/70) — the controlled, color-matched development-time cupping study; strongest evidence in the field.
- [Münchow et al., Beverages 2020 6(2):29](https://www.mdpi.com/2306-5710/6/2/29) — multi-study synthesis; color dominance.
- [Baggenstoss et al., JAFC 2008](https://pubmed.ncbi.nlm.nih.gov/18572953/) — Nestlé lab; HTST vs LTLT aroma kinetics.
- [Al-Shemmeri (Medium/EngD work)](https://medium.com/@markalshemmeri/the-effect-of-decaffeination-on-coffees-roasting-and-grinding-performance-229ea8450e66) — only controlled same-lot decaf-vs-regular roasting study; single lot, one method.

**Practitioner authorities (books/blogs):**
- [Scott Rao](https://www.scottrao.com/blog) — originator of declining-RoR/crash/flick/DTR doctrine; vast experience, evidence correlational and self-admittedly "not proof."
- [CoffeeMind / Morten Münchow](https://coffee-mind.com/why-rate-of-rise-is-a-bad-reference-point/) — SCA-affiliated researcher; most rigorous critique of RoR doctrine; sells courses (interest noted).
- Rob Hoos, *Modulating the Flavor Profile of Coffee* — respected phase-based alternative framework; own-roaster trials, not peer-reviewed.
- [Chris Kornman / Royal Coffee](https://royalcoffee.com/rate-of-rise-where-do-you-stand/) — importer education lead; best written defense of RoR as a tool.
- [Christopher Feran](https://christopherferan.com) — production roaster; thermodynamics reasoning, Sivetz history, airflow anecdote.
- [Barista Hustle](https://www.baristahustle.com/lesson/rs-4-08-probe-size-and-placement/) — probe-physics lessons citing measured experiments; air-roaster history.

**Retailer / community (SR800 & levels ground truth):**
- [Sweet Maria's Library](https://library.sweetmarias.com) — de facto authority on home-roast levels, decaf roasting, SR800 practice; machine-specific temps disclosed as such.
- [SR800 Tip Sheet (Sweet Maria's PDF)](https://www.sweetmarias.com/media/sebwite/productdownloads/s/r/sr800_tip_sheet_1.pdf) — the canonical SR800 operating doctrine.
- [Swiss Water blog](https://www.swisswater.com/blogs/sw/optimizing-the-roast-of-decaffeinated-coffee) + [IKAWA×Swiss Water](https://www.ikawacoffee.com/blog/how-to-roast-decaf-insights-from-swiss-water/) — deepest first-hand decaf expertise (commercial interest noted); publishes exact profiles.
- [Royal Coffee decaf practice](https://royalcoffee.com/reconsidering-how-we-roast-decaffeinated-coffees/) — instrumented (ColorTrack) decaf roast data.
- [Home-Barista](https://www.home-barista.com) / [Roast World community](https://community.roast.world) — practitioner reports; the source of the cross-rig FC-temp variance examples.
- [Coffee Review roast definitions](https://www.coffeereview.com/roast-definitions/) — dual-Agtron methodology standard.
- Perfect Daily Grind / MTPak / Cropster / Mill City Roasters / mill47 — trade education; good for consensus mechanics, weak as primary evidence.

*Biggest evidence gaps flagged during research: no color-matched controlled study of crash-vs-smooth RoR exists (and may be structurally impossible); no peer-reviewed blind fluid-bed vs drum cup comparison; fluid-bed heat-transfer coefficient figures could not be traced to a primary paper.*
