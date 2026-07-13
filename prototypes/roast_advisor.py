"""
Roast Advisor prototype (Fresh Roast SR800 / Artisan .alog)

Usage:
  python3 roast_advisor.py plan   TARGET.alog            -> prints settings plan from target roast
  python3 roast_advisor.py replay TARGET.alog LIVE.alog  -> replays LIVE roast against TARGET,
                                                            printing what the advisor would have said
The same advise() function would run in real time fed by live BT readings.
"""
import ast, sys
import numpy as np

RORDEV_PER_POWER = 5.0   # F/min RoR change per power step (rough SR800 estimate; refine w/ calibration roasts)
BT_GAIN = 15.0           # deg F of BT error treated as equal to one power step

def load_roast(path):
    d = ast.literal_eval(open(path).read())
    t = np.array(d['timex']); bt = np.array(d['temp2'])
    ti = d['timeindex']
    charge = t[ti[0]] if ti[0] > -1 else 0.0
    t = t - charge
    etypes = [e.lower() for e in d['etypes']]
    events = sorted(
        (t[i], etypes[ty], round((v - 1) * 10 / 11))
        for i, ty, v in zip(d['specialevents'], d['specialeventstype'], d['specialeventsvalue']))
    drop_t = t[ti[6]] if len(ti) > 6 and ti[6] > 0 else t[-1]
    fcs_t  = t[ti[2]] if len(ti) > 2 and ti[2] > 0 else None
    return dict(t=t, bt=bt, events=events, drop_t=drop_t, fcs_t=fcs_t, title=d.get('title', ''))

def setting_at(events, kind, tc):
    v = None
    for te, ty, val in events:
        if te <= tc and ty == kind: v = val
    return v

def ror_at(t, bt, tc, win=20):
    m = (t >= tc - win) & (t <= tc + win)
    return np.polyfit(t[m], bt[m], 1)[0] * 60 if m.sum() >= 3 else np.nan

def bt_at(t, bt, tc):
    return float(np.interp(tc, t, bt))

def fmt(s): m, x = divmod(int(round(s)), 60); return f"{m}:{x:02d}"

def print_plan(tgt):
    print(f"SETTINGS PLAN from target roast  (FCs {fmt(tgt['fcs_t']) if tgt['fcs_t'] else '?'}  DROP {fmt(tgt['drop_t'])})")
    print(f"{'time':>6} {'BT':>6}  action")
    last = {}
    for te, ty, val in tgt['events']:
        if last.get(ty) == val: continue
        last[ty] = val
        print(f"{fmt(te):>6} {bt_at(tgt['t'], tgt['bt'], te):6.0f}  {ty} -> {val}")

def advise(tgt, tc, live_bt, live_ror, cur_p):
    """Core advisor: called each tick with live readings. Returns (planned_p, planned_f, recommended_p, note)."""
    plan_p = setting_at(tgt['events'], 'power', tc)
    plan_f = setting_at(tgt['events'], 'fan', tc)
    tgt_bt = bt_at(tgt['t'], tgt['bt'], tc)
    tgt_ror = ror_at(tgt['t'], tgt['bt'], tc)
    bt_err = live_bt - tgt_bt              # + = running hot
    ror_err = live_ror - tgt_ror           # + = gaining too fast
    corr = -(bt_err / BT_GAIN * 0.5 + ror_err / RORDEV_PER_POWER * 0.5)
    rec = int(np.clip(round((plan_p if plan_p is not None else cur_p) + corr), 1, 9))
    if abs(bt_err) < 4 and abs(ror_err) < 3:
        note = "on curve"
    else:
        note = f"{'hot' if bt_err>0 else 'cool'} {abs(bt_err):.0f}F, RoR {'+' if ror_err>0 else ''}{ror_err:.0f}"
    return plan_p, plan_f, rec, note

def replay(tgt, live):
    print(f"{'time':>6} {'liveBT':>6} {'tgtBT':>6} {'liveRoR':>7} {'tgtRoR':>6} {'planP':>5} {'recP':>4} {'youP':>4}  note")
    for tc in range(60, int(min(tgt['drop_t'], live['drop_t'])), 30):
        lb = bt_at(live['t'], live['bt'], tc)
        lr = ror_at(live['t'], live['bt'], tc)
        yp = setting_at(live['events'], 'power', tc)
        pp, pf, rec, note = advise(tgt, tc, lb, lr, yp or 5)
        tb = bt_at(tgt['t'], tgt['bt'], tc); tr = ror_at(tgt['t'], tgt['bt'], tc)
        flag = '' if yp is None or rec == yp else ('  <-- advisor differs' if abs(rec - yp) > 1 else '')
        print(f"{fmt(tc):>6} {lb:6.0f} {tb:6.0f} {lr:7.1f} {tr:6.1f} {str(pp):>5} {rec:4d} {str(yp):>4}  {note}{flag}")

if __name__ == '__main__':
    mode = sys.argv[1]
    tgt = load_roast(sys.argv[2])
    if mode == 'plan':
        print_plan(tgt)
    else:
        live = load_roast(sys.argv[3])
        print_plan(tgt); print()
        replay(tgt, live)
