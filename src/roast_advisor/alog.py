"""Parse and decode Artisan .alog roast logs. Single source of truth.

Decoding rules (validated against the full archive):
- .alog files are Python dict literals -> ast.literal_eval, never JSON.
- timeindex = [CHARGE, DRY, FCs, FCe, SCs, SCe, DROP, COOL], indices into
  timex; -1 or 0 means "not marked" (CHARGE uses -1, the rest use 0).
- Artisan stores a 1-9 dial slider as v/10 + 1, so dial = round((v-1)*10/11).
- Event types are matched lowercase; only 'fan' and 'power' feed the model.
- temp2 is bean temp (BT); temp1 is ET and is usually -1.0 (no ET probe).
"""

import ast
from pathlib import Path

import numpy as np

TP_SEARCH_S = 180.0     # turning point must occur within this window after start
DRY_END_BT = 300.0      # drying phase ends when BT crosses this (DRY mark unreliable)
MIN_PLUNGE_F = 30.0     # BT drop needed to trust charge detection from the curve

CHARGE_MIN_PREHEAT_F = 250.0   # BT must have been this hot for a plunge to be a charge
CHARGE_MIN_DROP_F = 25.0       # how far below the recent peak BT must fall
CHARGE_MIN_RATE_F_S = 2.0      # and how fast it must be falling (F/s over ~4s)


def parse_alog_file(path):
    """Raw Artisan dict from an .alog file."""
    return ast.literal_eval(Path(path).read_text())


def decode_dial(value):
    """Artisan slider value -> 1-9 dial setting."""
    return int(round((value - 1) * 10 / 11))


def compute_ror(t, bt, window=15.0):
    """RoR (F/min) at each sample via regression over +/-window seconds.

    Raw 2s differences are far too noisy; this matches the brief's
    +/-10-20s smoothing requirement.
    """
    ror = np.full(len(t), np.nan)
    for i in range(len(t)):
        m = (t >= t[i] - window) & (t <= t[i] + window) & (bt > 0)
        if m.sum() >= 3:
            ror[i] = np.polyfit(t[m], bt[m], 1)[0] * 60
    return ror


def detect_charge(samples):
    """Charge time from the BT signature: a fast plunge off a >=250F preheat.

    THE charge rule — the live bridge streams into this during the roast and
    estimate_charge() replays recordings through it, so both timelines agree.
    samples: list of (t, bt), oldest first, spanning the last ~60s.
    Returns the plunge-start time (the last moment near the peak) or None.
    """
    if len(samples) < 8:
        return None
    t = np.array([s[0] for s in samples])
    bt = np.array([s[1] for s in samples])
    peak_bt = bt.max()
    if peak_bt < CHARGE_MIN_PREHEAT_F:
        return None
    if bt[-1] > peak_bt - CHARGE_MIN_DROP_F:
        return None
    recent = t >= t[-1] - 4.0
    if recent.sum() >= 3:
        rate = np.polyfit(t[recent], bt[recent], 1)[0]
        if rate > -CHARGE_MIN_RATE_F_S:
            return None
    # plunge start: the LAST moment BT was still near the preheat peak.
    # (On a flat noisy plateau the max itself lands at an arbitrary sample.)
    near_peak = np.where(bt >= peak_bt - 2.0)[0]
    return float(t[near_peak[-1]])


def estimate_charge(t, bt):
    """Charge time when no CHARGE mark exists: replay the recording through
    the live charge detector. Recordings may hold minutes of preheat (even a
    cold probe warming up first), so the whole pre-peak span is scanned —
    but only up to the global BT max, because the post-drop cooldown is
    itself a >=250F plunge and must never be mistaken for a charge.
    If the recording starts mid-plunge (or cold), t=0 is the best estimate.
    Returns (charge_time, method).
    """
    valid = np.where(bt > 0)[0]
    if len(valid) < 5:
        return 0.0, "assumed_zero"
    end = valid[np.argmax(bt[valid])]
    window = []
    for i in valid:
        if i > end:
            break
        window.append((float(t[i]), float(bt[i])))
        window = [(x, y) for x, y in window if x >= t[i] - 60]
        det = detect_charge(window)
        if det is not None:
            return det, "estimated"
    return 0.0, "assumed_zero"


def _mark_time(t, timeindex, slot):
    """Time of a timeindex mark, or None if not marked."""
    if len(timeindex) > slot and timeindex[slot] > 0:
        return float(t[timeindex[slot]])
    return None


def load_roast(path):
    """Load one .alog into a normalized dict; all times in seconds from charge."""
    d = parse_alog_file(path)
    t = np.asarray(d["timex"], dtype=float)
    bt = np.asarray(d["temp2"], dtype=float)
    et = np.asarray(d["temp1"], dtype=float)
    mode_original = d.get("mode", "F")
    if mode_original == "C":
        # normalize to F so every threshold and model shares one scale;
        # non-positive values are no-reading sentinels, never temperatures
        bt = np.where(bt > 0, bt * 9 / 5 + 32, bt)
        et = np.where(et > 0, et * 9 / 5 + 32, et)
    ti = d.get("timeindex", [-1, 0, 0, 0, 0, 0, 0, 0])

    if len(t) < 5 or not (bt > 0).any():
        raise ValueError("empty or probe-less recording (no valid BT samples)")

    if ti[0] > -1:
        charge, charge_method = float(t[ti[0]]), "marked"
    else:
        charge, charge_method = estimate_charge(t, bt)
    t = t - charge

    etypes = [e.lower() for e in d.get("etypes", [])]
    events = []
    for i, ty, v in zip(
        d.get("specialevents", []),
        d.get("specialeventstype", []),
        d.get("specialeventsvalue", []),
    ):
        kind = etypes[ty] if ty < len(etypes) else "?"
        if kind in ("fan", "power"):
            events.append((float(t[i]), kind, decode_dial(v)))
    events.sort()

    drop_t = _mark_time(t, ti, 6)
    if drop_t is None:
        drop_t = float(t[-1])
        drop_marked = False
    else:
        drop_marked = True
    fcs_t = _mark_time(t, ti, 2)
    dry_marked_t = _mark_time(t, ti, 1)

    ror = compute_ror(t, bt)

    # turning point: BT minimum in the first two minutes after charge
    post = (t >= 0) & (t <= 120) & (bt > 0)
    if post.any():
        idx = np.where(post)[0]
        tp_i = idx[np.argmin(bt[idx])]
        tp_t, tp_bt = float(t[tp_i]), float(bt[tp_i])
    else:
        tp_t = tp_bt = None

    # drying ends at the 300F crossing (manual DRY mark is only a cross-check)
    dry_t = None
    hot = (t > (tp_t or 0)) & (bt >= DRY_END_BT)
    if hot.any():
        dry_t = float(t[np.where(hot)[0][0]])

    def bt_at(tc):
        return float(np.interp(tc, t[bt > 0], bt[bt > 0])) if tc is not None else None

    weight = d.get("weight", [0, 0, "g"])
    to_g = 453.592 if weight[2] == "lb" else 1.0

    return {
        "path": str(path),
        "uuid": d.get("roastUUID", ""),
        "title": d.get("title", ""),
        "beans": d.get("beans", ""),
        "date": d.get("roastisodate", ""),
        "epoch": d.get("roastepoch"),
        "mode": "F",  # temps always normalized to F on load
        "mode_original": mode_original,
        "weight_in_g": float(weight[0]) * to_g,
        "weight_out_g": float(weight[1]) * to_g,
        "ambient_temp": d.get("ambientTemp"),
        "ambient_humidity": d.get("ambient_humidity"),
        "t": t,
        "bt": bt,
        "et": et,
        "ror": ror,
        "events": events,
        "charge_method": charge_method,
        "charge_raw_t": charge,
        "tp_t": tp_t,
        "tp_bt": tp_bt,
        "dry_t": dry_t,
        "dry_marked_t": dry_marked_t,
        "fcs_t": fcs_t,
        "fcs_bt": bt_at(fcs_t),
        "drop_t": drop_t,
        "drop_bt": bt_at(drop_t),
        "drop_marked": drop_marked,
        "computed": d.get("computed", {}),
    }


def setting_at(events, kind, tc):
    """Last fan/power value set at or before time tc, or None."""
    v = None
    for te, ty, val in events:
        if te <= tc and ty == kind:
            v = val
    return v


def phase_of(t, fcs_t, dry_t):
    """drying / maillard / development label for a time from charge."""
    if dry_t is not None and t < dry_t:
        return "drying"
    if fcs_t is not None and t >= fcs_t:
        return "development"
    return "maillard" if dry_t is not None else "drying"
