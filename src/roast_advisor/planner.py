"""Turn a target curve + roast history into a cue card of fan/power settings.

kNN over historical (BT, RoR) -> (fan, power): interpolates the operator's own
demonstrated behavior. Reliable near historical profiles, degrades gracefully;
deliberately NOT a causal thermal model (see project brief, "Findings so far").
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# kNN distance scaling: 15F of BT counts the same as 5 F/min of RoR
BT_SCALE = 15.0
ROR_SCALE = 5.0
K_NEIGHBORS = 15

# fixed opening block from the roast-day workflow: fan 9 / power 1 until ~1:10.
# History below ~200F is sparse, so the kNN never plans inside this block.
OPENING_FAN = 9
OPENING_POWER = 1
OPENING_END_S = 70.0

CHECK_STEP_S = 10.0
CHANGE_DEADBAND = 0.6   # don't move a dial until the prediction is clearly away from it
NO_CHANGE_TAIL_S = 30.0  # a dial change in the last seconds before drop is pointless


def predict_settings(S, bt, ror, k=K_NEIGHBORS):
    """Weighted kNN in (BT, RoR) space -> (fan, power) as floats."""
    d = np.sqrt(((S[:, 0] - bt) / BT_SCALE) ** 2 + ((S[:, 1] - ror) / ROR_SCALE) ** 2)
    idx = np.argsort(d)[:k]
    w = 1 / (d[idx] + 0.3)
    return float(np.sum(S[idx, 2] * w) / w.sum()), float(np.sum(S[idx, 3] * w) / w.sum())


def _smooth(vals, half=2):
    """Running median (+/-2 checkpoints = +/-20s): early-roast history is sparse,
    so raw kNN output wobbles around the trend; the cue card wants the trend."""
    v = np.asarray(vals, dtype=float)
    out = v.copy()
    for i in range(len(v)):
        out[i] = np.median(v[max(0, i - half) : i + half + 1])
    return out


def _plan_dials(preds, start, ts, total_s):
    """Float predictions -> planned dial per checkpoint, with a deadband.

    The dial only moves when the prediction sits clearly away from the current
    setting, which stops the 3 -> 2 -> 3 flip-flops a plain round() produces.
    """
    preds = _smooth(preds)
    cur = start
    dials = []
    for t, p in zip(ts, preds):
        if t <= total_s - NO_CHANGE_TAIL_S and abs(p - cur) >= CHANGE_DEADBAND:
            cur = int(np.clip(round(p), 1, 9))
        dials.append(cur)
    return dials


def make_plan(target, S):
    """Checkpoint recommendations + collapsed list of setting changes."""
    c = target["curve"]
    total_s = target["meta"]["constraints"]["total_s"]

    ts = np.arange(OPENING_END_S, total_s + 1, CHECK_STEP_S)
    bts = np.interp(ts, c["t"], c["bt"])
    rors = np.interp(ts, c["t"], c["ror"])
    raw = [predict_settings(S, b, r) for b, r in zip(bts, rors)]
    fans = _plan_dials([f for f, _ in raw], OPENING_FAN, ts, total_s)
    powers = _plan_dials([p for _, p in raw], OPENING_POWER, ts, total_s)

    checkpoints = [
        {"t": float(t), "bt": round(float(b), 1), "ror": round(float(r), 1),
         "fan": f, "power": p}
        for t, b, r, f, p in zip(ts, bts, rors, fans, powers)
    ]

    changes = [
        {"t": 0.0, "setting": "fan", "value": OPENING_FAN, "bt": c["bt"][0]},
        {"t": 0.0, "setting": "power", "value": OPENING_POWER, "bt": c["bt"][0]},
    ]
    last = {"fan": OPENING_FAN, "power": OPENING_POWER}
    for cp in checkpoints:
        for setting in ("fan", "power"):
            if cp[setting] != last[setting]:
                changes.append(
                    {"t": cp["t"], "setting": setting, "value": cp[setting], "bt": cp["bt"]}
                )
                last[setting] = cp[setting]

    return {
        "target": target["meta"]["name"],
        "opening": {"fan": OPENING_FAN, "power": OPENING_POWER, "until_s": OPENING_END_S},
        "checkpoints": checkpoints,
        "changes": changes,
    }


def fmt(s):
    m, x = divmod(int(round(s)), 60)
    return f"{m}:{x:02d}"


def cue_card_text(target, plan):
    m = target["meta"]
    con, der = m["constraints"], m["derived"]
    lines = [
        f"CUE CARD — {m['name']}",
        f"Preheat {con['charge_bt']:.0f}F. Charge. "
        f"FCs ~{der['fcs_time']} @{con['fcs_bt']:.0f}F, "
        f"DROP {fmt(con['total_s'])} @{con['drop_bt']:.0f}F "
        f"(DTR {con['dtr']:.0%}, dev {der['dev_time_min']:.1f} min)",
        "",
        f"  0:00        Fan {plan['opening']['fan']} / Power {plan['opening']['power']}"
        f"   (opening block until {fmt(plan['opening']['until_s'])})",
    ]
    by_time = {}
    for ch in plan["changes"]:
        if ch["t"] > 0:
            by_time.setdefault(ch["t"], {})[ch["setting"]] = ch
    state = dict(fan=plan["opening"]["fan"], power=plan["opening"]["power"])
    for t in sorted(by_time):
        for setting, ch in by_time[t].items():
            state[setting] = ch["value"]
        bt = list(by_time[t].values())[0]["bt"]
        lines.append(f"  {fmt(t):<5} ~{bt:3.0f}F  Fan {state['fan']} / Power {state['power']}")
    lines += [
        "",
        "Watch points:",
        f"  ~{der['fcs_time']} @{con['fcs_bt']:.0f}F  first crack should start",
        f"  {fmt(con['total_s'])} @{con['drop_bt']:.0f}F  DROP",
        "If RoR runs hot at a checkpoint: power -1. If cold: power +1.",
    ]
    return "\n".join(lines)


def plot_plan(target, plan, out_path):
    c = target["curve"]
    tm = np.asarray(c["t"]) / 60
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(11, 9), sharex=True, gridspec_kw={"height_ratios": [3, 2, 1.4]}
    )
    ax1.plot(tm, c["bt"], "b-", lw=2.5, label="Target BT")
    for ch in plan["changes"]:
        if ch["t"] > 0:
            ax1.axvline(ch["t"] / 60, color="gray", alpha=0.25, lw=0.8)
    der, con = target["meta"]["derived"], target["meta"]["constraints"]
    ax1.plot([der["fcs_s"] / 60], [con["fcs_bt"]], "ko")
    ax1.annotate(f"FCs {der['fcs_time']}", (der["fcs_s"] / 60, con["fcs_bt"]),
                 textcoords="offset points", xytext=(8, -12), fontsize=9)
    ax1.set_ylabel("Bean temp (F)")
    ax1.grid(alpha=0.3)
    ax1.legend()
    ax1.set_title(f"Plan for {target['meta']['name']}")

    ax2.plot(tm, c["ror"], "r-", lw=2.5, label="Target RoR")
    ax2.set_ylabel("RoR (F/min)")
    ax2.grid(alpha=0.3)
    ax2.legend()

    cps = plan["checkpoints"]
    cp_t = [cp["t"] / 60 for cp in cps]
    open_t = [0, plan["opening"]["until_s"] / 60]
    ax3.step(open_t + cp_t, [plan["opening"]["fan"]] * 2 + [cp["fan"] for cp in cps],
             where="post", color="teal", lw=2, label="Fan")
    ax3.step(open_t + cp_t, [plan["opening"]["power"]] * 2 + [cp["power"] for cp in cps],
             where="post", color="darkorange", lw=2, label="Power")
    ax3.set_ylim(0, 10)
    ax3.set_yticks(range(1, 10, 2))
    ax3.set_ylabel("Dial")
    ax3.set_xlabel("Minutes from charge")
    ax3.grid(alpha=0.3)
    ax3.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=110)
    plt.close(fig)


def save_plan(target, plan, plans_dir="plans"):
    plans_dir = Path(plans_dir)
    name = target["meta"]["name"]
    (plans_dir / f"{name}_plan.json").write_text(json.dumps(plan, indent=1))
    card = cue_card_text(target, plan)
    (plans_dir / f"{name}_cue_card.txt").write_text(card + "\n")
    plot_plan(target, plan, plans_dir / f"{name}_plan.png")
    return card
