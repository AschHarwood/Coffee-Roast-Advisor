"""Score a finished roast against its target curve and its cue-card plan.

Two separate scores, kept distinct per the brief:
1. Profile adherence — did the roast follow the designed curve?
2. Advisor adherence — did the operator follow the plan, and when they
   deviated, did the deviation help or hurt?
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import alog
from .planner import fmt

ROR_CRASH_F_MIN = 4.0    # RoR below this before FCs+30s counts as a crash
ROR_FLICK_F_MIN = 2.0    # RoR rising more than this late in the roast is a flick
APPLY_WINDOW_S = 45.0    # a plan change counts as applied if matched within this


def _interp_target(target, ts):
    c = target["curve"]
    bt = np.interp(ts, c["t"], c["bt"])
    ok = ~np.isnan(c["ror"])
    ror = np.interp(ts, c["t"][ok], c["ror"][ok])
    return bt, ror


def profile_score(target, roast):
    meta = target["meta"]
    con, der = meta["constraints"], meta["derived"]
    compare_from = meta.get("compare_from_s", 50.0)

    t, bt, ror = roast["t"], roast["bt"], roast["ror"]
    end = min(roast["drop_t"], con["total_s"])
    m = (t >= compare_from) & (t <= end) & (bt > 0)
    ts = t[m]
    tgt_bt, tgt_ror = _interp_target(target, ts)
    bt_err = bt[m] - tgt_bt
    ror_err = ror[m] - tgt_ror

    fcs_t = roast["fcs_t"] if roast["fcs_t"] else der["fcs_s"]
    phases = np.array([alog.phase_of(x, fcs_t, roast["dry_t"]) for x in ts])
    by_phase = {}
    for ph in ("drying", "maillard", "development"):
        pm = phases == ph
        if pm.any():
            by_phase[ph] = {
                "bt_err_mean": float(np.mean(np.abs(bt_err[pm]))),
                "bt_err_max": float(np.max(np.abs(bt_err[pm]))),
                "ror_err_mean": float(np.nanmean(np.abs(ror_err[pm]))),
            }

    milestones = {
        "tp": {
            "t": roast["tp_t"], "t_target": con["tp_s"],
            "bt": roast["tp_bt"], "bt_target": con["tp_bt"],
        },
        "fcs": {
            "t": roast["fcs_t"], "t_target": der["fcs_s"],
            "bt": roast["fcs_bt"], "bt_target": con["fcs_bt"],
        },
        "drop": {
            "t": roast["drop_t"], "t_target": con["total_s"],
            "bt": roast["drop_bt"], "bt_target": con["drop_bt"],
        },
    }
    for ms in milestones.values():
        ms["dt"] = ms["t"] - ms["t_target"] if ms["t"] is not None else None
        ms["dbt"] = ms["bt"] - ms["bt_target"] if ms["bt"] is not None else None

    dtr = (
        (roast["drop_t"] - roast["fcs_t"]) / roast["drop_t"]
        if roast["fcs_t"]
        else None
    )

    # RoR shape checks on the actual curve
    mid = (ts > compare_from + 30) & (ts < fcs_t + 30)
    crash = bool(mid.any() and np.nanmin(ror[m][mid]) < ROR_CRASH_F_MIN)
    late = ts > max(fcs_t - 60, compare_from)
    flick = False
    if late.sum() > 15:
        r_late = ror[m][late]
        t_late = ts[late]
        for i in range(len(t_late)):
            j = np.searchsorted(t_late, t_late[i] + 30)
            if j < len(t_late) and r_late[j] - r_late[i] > ROR_FLICK_F_MIN:
                flick = True
                break

    return {
        "milestones": milestones,
        "dtr": {"actual": dtr, "target": con["dtr"]},
        "bt_err_mean": float(np.mean(np.abs(bt_err))),
        "bt_err_max": float(np.max(np.abs(bt_err))),
        "by_phase": by_phase,
        "ror_crash": crash,
        "ror_flick": flick,
    }


def advisor_score(target, plan, roast):
    """Did the operator follow the cue card, and did deviations help?"""
    t, bt = roast["t"], roast["bt"]

    def bt_err_at(tc):
        ok = bt > 0
        actual = float(np.interp(tc, t[ok], bt[ok]))
        tgt_bt, _ = _interp_target(target, np.array([tc]))
        return actual - float(tgt_bt[0])

    rows = []
    for ch in plan["changes"]:
        if ch["t"] <= 0:
            continue
        applied_val = alog.setting_at(roast["events"], ch["setting"], ch["t"] + APPLY_WINDOW_S)
        matches = [
            te for te, ty, v in roast["events"]
            if ty == ch["setting"] and v == ch["value"]
            and ch["t"] - APPLY_WINDOW_S <= te <= ch["t"] + 2 * APPLY_WINDOW_S
        ]
        row = {
            "t": ch["t"],
            "setting": ch["setting"],
            "recommended": ch["value"],
            "actual": applied_val,
        }
        if matches:
            row["applied"] = True
            row["late_s"] = round(min(matches) - ch["t"], 1)
        else:
            row["applied"] = False
            row["late_s"] = None
            # deviation: did the curve move toward or away from target after?
            before = abs(bt_err_at(ch["t"]))
            after_t = min(ch["t"] + 60, roast["drop_t"])
            after = abs(bt_err_at(after_t))
            row["deviation_effect"] = "helped" if after < before - 1 else (
                "hurt" if after > before + 1 else "neutral"
            )
        rows.append(row)

    n = len(rows)
    applied = sum(r["applied"] for r in rows)

    # advisor stability: direction reversals within 60s, per setting
    reversals = 0
    for setting in ("fan", "power"):
        seq = [ch for ch in plan["changes"] if ch["setting"] == setting]
        for a, b, c in zip(seq, seq[1:], seq[2:]):
            d1, d2 = b["value"] - a["value"], c["value"] - b["value"]
            if d1 * d2 < 0 and c["t"] - b["t"] <= 60:
                reversals += 1

    return {
        "n_recommendations": n,
        "n_applied": applied,
        "changes": rows,
        "plan_reversals_within_60s": reversals,
    }


def plot_overlay(target, roast, plan, out_path):
    c = target["curve"]
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(11, 10), sharex=True, gridspec_kw={"height_ratios": [3, 2, 1.4]}
    )
    ok = roast["bt"] > 0
    tm_t = np.asarray(c["t"]) / 60
    tm_r = roast["t"][ok] / 60
    ax1.plot(tm_t, c["bt"], "b--", lw=1.8, label="Target BT")
    ax1.plot(tm_r, roast["bt"][ok], "b-", lw=2.2, label="Actual BT")
    if roast["fcs_t"]:
        ax1.axvline(roast["fcs_t"] / 60, color="brown", ls=":", alpha=0.7)
        ax1.text(roast["fcs_t"] / 60, ax1.get_ylim()[0], " FCs", color="brown")
    ax1.set_ylabel("Bean temp (F)")
    ax1.grid(alpha=0.3)
    ax1.legend()
    ax1.set_title(f"{Path(roast['path']).name} vs {target['meta']['name']}")

    ax2.plot(tm_t, c["ror"], "r--", lw=1.8, label="Target RoR")
    ax2.plot(tm_r, roast["ror"][ok], "r-", lw=1.6, label="Actual RoR")
    ax2.set_ylim(0, 50)
    ax2.set_ylabel("RoR (F/min)")
    ax2.grid(alpha=0.3)
    ax2.legend()

    for setting, color in (("fan", "teal"), ("power", "darkorange")):
        ev = [(te, v) for te, ty, v in roast["events"] if ty == setting]
        if ev:
            te, v = zip(*ev)
            ax3.step([x / 60 for x in te], v, where="post", color=color, lw=2,
                     label=f"{setting} (actual)")
        if plan:
            pl = [(ch["t"], ch["value"]) for ch in plan["changes"] if ch["setting"] == setting]
            tp_, vp = zip(*pl)
            ax3.step([x / 60 for x in tp_], vp, where="post", color=color, lw=1.2,
                     ls="--", alpha=0.7, label=f"{setting} (plan)")
    ax3.set_ylim(0, 10)
    ax3.set_ylabel("Dial")
    ax3.set_xlabel("Minutes from charge")
    ax3.grid(alpha=0.3)
    ax3.legend(loc="lower right", fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=110)
    plt.close(fig)


def render_text(score, adv):
    L = ["PROFILE ADHERENCE (actual vs target)"]
    for name, ms in score["milestones"].items():
        if ms["t"] is None:
            L.append(f"  {name.upper():<5} not marked")
            continue
        L.append(
            f"  {name.upper():<5} {fmt(ms['t'])} @{ms['bt']:.0f}F   "
            f"target {fmt(ms['t_target'])} @{ms['bt_target']:.0f}F   "
            f"({ms['dt']:+.0f}s, {ms['dbt']:+.0f}F)"
        )
    d = score["dtr"]
    if d["actual"]:
        L.append(f"  DTR   {d['actual']:.1%} vs designed {d['target']:.0%}")
    L.append(f"  BT error: mean {score['bt_err_mean']:.1f}F, max {score['bt_err_max']:.1f}F")
    for ph, s in score["by_phase"].items():
        L.append(
            f"    {ph:<12} BT mean {s['bt_err_mean']:.1f}F / max {s['bt_err_max']:.1f}F, "
            f"RoR mean {s['ror_err_mean']:.1f} F/min"
        )
    L.append(f"  RoR crash before FCs+30s: {'YES' if score['ror_crash'] else 'no'}   "
             f"late RoR flick: {'YES' if score['ror_flick'] else 'no'}")
    if adv:
        L.append("")
        L.append("ADVISOR ADHERENCE (actual settings vs plan)")
        L.append(f"  recommendations applied: {adv['n_applied']}/{adv['n_recommendations']}")
        for r in adv["changes"]:
            if r["applied"]:
                L.append(f"  {fmt(r['t'])} {r['setting']} -> {r['recommended']}: "
                         f"applied ({r['late_s']:+.0f}s)")
            else:
                L.append(f"  {fmt(r['t'])} {r['setting']} -> {r['recommended']}: "
                         f"NOT applied (stayed {r['actual']}), deviation {r['deviation_effect']}")
        L.append(f"  plan reversals within 60s: {adv['plan_reversals_within_60s']}")
    return "\n".join(L)


def run(target_path, roast_path, plan_path=None, reports_dir="reports"):
    from .designer import load_target

    target = load_target(target_path)
    roast = alog.load_roast(roast_path)
    plan = None
    if plan_path is None:
        candidate = Path(target_path).parent / f"{target['meta']['name']}_plan.json"
        plan_path = candidate if candidate.exists() else None
    if plan_path:
        plan = json.loads(Path(plan_path).read_text())

    score = profile_score(target, roast)
    adv = advisor_score(target, plan, roast) if plan else None

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(exist_ok=True)
    stem = f"{Path(roast_path).stem}_vs_{target['meta']['name']}"
    plot_overlay(target, roast, plan, reports_dir / f"{stem}.png")
    scorecard = {"profile": score, "advisor": adv}
    (reports_dir / f"{stem}.json").write_text(json.dumps(scorecard, indent=1, default=str))
    text = render_text(score, adv)
    (reports_dir / f"{stem}.txt").write_text(text + "\n")
    return text, reports_dir / f"{stem}.png"
