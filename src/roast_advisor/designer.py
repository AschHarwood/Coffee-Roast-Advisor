"""Design a target BT/RoR curve from roast constraints.

Ported from prototypes/design_city_target.py: a Rao-style continuously
declining RoR, linear in each of the two segments (TP->FCs, FCs->DROP),
with each segment's endpoints solved so the BT curve integrates exactly
to the constrained milestone temperatures.
"""

import json
from pathlib import Path

import numpy as np


SHAPE_KNEE_U = 0.7  # history shape used as-is until here, then tapered to FCs


def _history_ror_main(ror_shape, avg, r_fcs):
    """Main-phase RoR from the measured machine shape.

    Pure scaling of the historical shape until SHAPE_KNEE_U, then a linear
    taper into r_fcs so the curve meets the development segment exactly.
    The scale solves the integral so BT still lands on fcs_bt on the dot.
    """
    u_grid, s = ror_shape
    fine = np.linspace(0, SHAPE_KNEE_U, 200)
    area = float(np.trapezoid(np.interp(fine, u_grid, s), fine))
    s_knee = float(np.interp(SHAPE_KNEE_U, u_grid, s))
    tail = (1 - SHAPE_KNEE_U) / 2
    scale = (avg - tail * r_fcs) / (area + tail * s_knee)
    if scale <= 0:
        raise ValueError(
            "constraints demand a lower average RoR than the development "
            "segment alone provides — lengthen the roast or raise fcs_bt"
        )

    def ror_main(u):
        if u <= SHAPE_KNEE_U:
            return scale * float(np.interp(u, u_grid, s))
        w = (u - SHAPE_KNEE_U) / (1 - SHAPE_KNEE_U)
        return scale * s_knee + (r_fcs - scale * s_knee) * w

    return ror_main, scale


def design_target(
    name,
    total_s=600.0,
    dtr=0.22,
    fcs_bt=392.0,
    drop_bt=406.0,
    charge_bt=300.0,
    tp_s=50.0,
    tp_bt=140.0,
    ror_at_drop=5.0,
    description="",
    ror_shape=None,
    dev_time_s=None,
):
    """Build the target curve dict (same schema as plans/target_city_10min.json).

    dev_time_s: development time (FC onset -> drop) in seconds. This is the
    PRIMARY design variable per the knowledge brief (controlled evidence backs
    absolute dev time; DTR is derived display info). If omitted, dtr is used.

    ror_shape: optional (u_grid, shape) from dataset.median_ror_shape() — the
    machine's measured main-phase RoR profile. Without it the main phase is a
    linear RoR decline, which no real probe produces (RoR is ~0 at the turning
    point and rebounds violently); prefer the measured shape for real roasts.
    """
    if dev_time_s is not None:
        dtr = dev_time_s / total_s
    fcs_s = total_s * (1 - dtr)
    dev_min = (total_s - fcs_s) / 60
    # development: linear RoR from r_fcs down to ror_at_drop, integrating to (drop-fcs) BT
    r_fcs = 2 * (drop_bt - fcs_bt) / dev_min - ror_at_drop
    main_min = (fcs_s - tp_s) / 60
    avg_main = (fcs_bt - tp_bt) / main_min
    if ror_shape is not None:
        ror_main, shape_scale = _history_ror_main(ror_shape, avg_main, r_fcs)
        r_tp = ror_main(0.0)
    else:
        # legacy: linear RoR from r_tp down to r_fcs
        r_tp = 2 * avg_main - r_fcs
        shape_scale = None

        def ror_main(u):
            return r_tp + (r_fcs - r_tp) * u

    def ror(t):
        if t < tp_s:
            return None
        if t <= fcs_s:
            return ror_main((t - tp_s) / (fcs_s - tp_s))
        return r_fcs + (ror_at_drop - r_fcs) * (t - fcs_s) / (total_s - fcs_s)

    ts = np.arange(0, total_s + 1, 2.0)
    bt = np.empty(len(ts))
    i_tp = int(np.searchsorted(ts, tp_s))
    # pre-TP segment is cosmetic: quadratic descent charge_bt -> tp_bt, flat at TP
    u = ts[: i_tp + 1] / tp_s
    bt[: i_tp + 1] = charge_bt + (tp_bt - charge_bt) * (2 * u - u * u)
    for i in range(i_tp + 1, len(ts)):
        bt[i] = bt[i - 1] + (ror(ts[i - 1]) + ror(ts[i])) / 2 * 2 / 60

    def fmt(s):
        m, x = divmod(int(round(s)), 60)
        return f"{m}:{x:02d}"

    return {
        "meta": {
            "name": name,
            "description": description,
            "units": "F, seconds from charge",
            "constraints": {
                "total_s": total_s, "dtr": dtr, "fcs_bt": fcs_bt,
                "drop_bt": drop_bt, "charge_bt": charge_bt,
                "tp_s": tp_s, "tp_bt": tp_bt, "ror_at_drop": ror_at_drop,
            },
            "derived": {
                "fcs_s": fcs_s, "fcs_time": fmt(fcs_s),
                "ror_at_tp": round(r_tp, 1), "ror_at_fcs": round(r_fcs, 1),
                "dev_time_min": round(dev_min, 2),
                **(
                    {
                        "ror_shape": "history-median",
                        "ror_peak": round(max(ror(t) for t in ts if ror(t) is not None), 1),
                    }
                    if ror_shape is not None
                    else {}
                ),
            },
            "compare_from_s": tp_s,
        },
        "curve": {
            "t": [float(t) for t in ts],
            "bt": [round(float(v), 2) for v in bt],
            "ror": [round(ror(t), 2) if ror(t) is not None else None for t in ts],
        },
    }


# Hard-constraint thresholds from the knowledge brief §8 (all [consensus])
STALL_ROR = 0.0
NEAR_STALL_ROR = 2.5      # F/min sustained below this pre-FC = bake risk
NEAR_STALL_MAX_S = 60.0
MIN_DEV_S = 60.0
MIN_DEV_FRACTION = 0.08
SOFT_MIN_DROP_ROR = 4.0   # below this is contested anti-"baked" lore -> warn


def validate_target(target):
    """Check a designed curve against the brief's encodable constraints.

    Returns {"hard": [...], "soft": [...]} — hard violations mean the curve
    should not be handed to the user; soft ones are contested-doctrine
    warnings to surface alongside the plan.
    """
    import numpy as np

    con, der = target["meta"]["constraints"], target["meta"]["derived"]
    c = target["curve"]
    t = np.asarray(c["t"], dtype=float)
    ror = np.asarray(
        [np.nan if v is None else v for v in c["ror"]], dtype=float
    )
    fcs_s, total_s = der["fcs_s"], con["total_s"]
    main = (t > con["tp_s"]) & (t <= total_s)
    hard, soft = [], []

    if np.nanmin(ror[main]) <= STALL_ROR:
        hard.append("stall: target RoR <= 0 between turning point and drop")

    pre_fc = main & (t < fcs_s)
    slow = ror[pre_fc] < NEAR_STALL_ROR
    if slow.any():
        # longest consecutive run of near-stall samples (2s grid)
        run = max_run = 0
        for flag in slow:
            run = run + 1 if flag else 0
            max_run = max(max_run, run)
        step = float(np.median(np.diff(t)))
        if max_run * step > NEAR_STALL_MAX_S:
            hard.append(
                f"near-stall: RoR < {NEAR_STALL_ROR} F/min for "
                f">{NEAR_STALL_MAX_S:.0f}s before FC (bake risk)"
            )

    dev_s = total_s - fcs_s
    if dev_s < MIN_DEV_S or dev_s / total_s < MIN_DEV_FRACTION:
        hard.append(
            f"under-development: {dev_s:.0f}s after FC "
            f"(minimum {MIN_DEV_S:.0f}s and {MIN_DEV_FRACTION:.0%} of total)"
        )

    if con["ror_at_drop"] < SOFT_MIN_DROP_ROR:
        soft.append(
            f"drop RoR {con['ror_at_drop']} < {SOFT_MIN_DROP_ROR} F/min "
            "(contested anti-baked heuristic)"
        )

    return {"hard": hard, "soft": soft}


def load_target(path):
    tgt = json.loads(Path(path).read_text())
    c = tgt["curve"]
    c["t"] = np.asarray(c["t"], dtype=float)
    c["bt"] = np.asarray(c["bt"], dtype=float)
    c["ror"] = np.asarray([np.nan if v is None else v for v in c["ror"]], dtype=float)
    return tgt


def save_target(tgt, plans_dir="plans"):
    path = Path(plans_dir) / f"target_{tgt['meta']['name']}.json"
    path.write_text(json.dumps(tgt, indent=1))
    return path
