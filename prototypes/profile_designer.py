"""
Profile Designer: build an ideal BT/RoR curve from roast constraints,
then predict SR800 fan/power settings from your roast history (kNN on BT+RoR).
"""
import ast, glob
import numpy as np

# ---------- 1. Design target curve ----------
# Constraints (user):
TP_T, TP_BT   = 50, 140.0     # turning point ~0:50 after charge, beans bottom out at 140F
FCS_BT        = 392.0
DROP_T, DROP_BT = 540, 407.0  # 9:00 total
DEV_RATIO     = 0.19          # development time as fraction of total -> FCs at ~7:17

FCS_T = DROP_T * (1 - DEV_RATIO)          # 437s = 7:17
# development RoR: (407-392) over 1:43 -> declining ~10 -> ~7
R_FCS = 2 * (DROP_BT - FCS_BT) / ((DROP_T - FCS_T)/60) - 7.0   # solve linear decline ending at 7 F/min
# main phase: linear declining RoR from R0 at TP to R_FCS at FCs, integrating to (392-140)
avg_needed = (FCS_BT - TP_BT) / ((FCS_T - TP_T)/60)
R0 = 2*avg_needed - R_FCS

def target_ror(t):
    """F/min at t seconds after charge."""
    if t < TP_T:   # charge drop then turn: not modeled, cosmetic ramp
        return None
    if t <= FCS_T:
        return R0 + (R_FCS - R0)*(t - TP_T)/(FCS_T - TP_T)
    return R_FCS + (7.0 - R_FCS)*(t - FCS_T)/(DROP_T - FCS_T)

def build_curve(dt=2):
    ts=[TP_T]; bts=[TP_BT]
    t=TP_T
    while t < DROP_T:
        r=target_ror(t)
        t+=dt
        bts.append(bts[-1]+r*dt/60)
        ts.append(t)
    return np.array(ts), np.array(bts)

# ---------- 2. Predict settings from history ----------
def load_roast(path):
    d=ast.literal_eval(open(path).read())
    t=np.array(d['timex']); bt=np.array(d['temp2'])
    ti=d['timeindex']; charge=t[ti[0]] if ti[0]>-1 else 0.0
    t=t-charge
    etypes=[e.lower() for e in d['etypes']]
    events=sorted((t[i],etypes[ty],round((v-1)*10/11)) for i,ty,v in
                  zip(d['specialevents'],d['specialeventstype'],d['specialeventsvalue']))
    drop=t[ti[6]] if len(ti)>6 and ti[6]>0 else t[-1]
    return t,bt,events,drop

def history_samples(files):
    """(BT, RoR, fan, power) at every 10s of every historical roast."""
    S=[]
    for p in files:
        t,bt,events,drop=load_roast(p)
        for tc in np.arange(40,drop,10):
            m=(t>=tc-20)&(t<=tc+20)
            if m.sum()<3: continue
            ror=np.polyfit(t[m],bt[m],1)[0]*60
            b=float(np.interp(tc,t,bt))
            f=pw=None
            for te,ty,val in events:
                if te<=tc:
                    if ty=='fan': f=val
                    elif ty=='power': pw=val
            if f is None or pw is None: continue
            S.append((b,ror,f,pw))
    return np.array(S)

def predict_settings(S, bt, ror, k=15):
    """kNN in (BT, RoR) space; RoR scaled so 5 F/min ~ 15F BT."""
    d=np.sqrt(((S[:,0]-bt)/15)**2 + ((S[:,1]-ror)/5)**2)
    idx=np.argsort(d)[:k]
    w=1/(d[idx]+.3)
    fan=np.sum(S[idx,2]*w)/w.sum()
    pw =np.sum(S[idx,3]*w)/w.sum()
    return fan,pw

if __name__=='__main__':
    files=[p for p in sorted(glob.glob('/sessions/confident-trusting-curie/mnt/uploads/*.alog')) if '24-03' not in p]
    S=history_samples(files)
    ts,bts=build_curve()
    print(f"Designed curve: TP {TP_T}s@{TP_BT:.0f}F -> FCs {int(FCS_T)//60}:{int(FCS_T)%60:02d}@{FCS_BT:.0f}F -> DROP 9:00@{DROP_BT:.0f}F")
    print(f"RoR: starts {R0:.1f} F/min at TP, declines to {R_FCS:.1f} at FCs, {7.0:.0f} at drop")
    print(f"history samples: {len(S)}")
    print(f"\n{'time':>6} {'BT':>5} {'RoR':>5} {'fan*':>5} {'pow*':>5}")
    for tc in np.arange(60,DROP_T+1,30):
        b=float(np.interp(tc,ts,bts)); r=target_ror(tc)
        f,pw=predict_settings(S,b,r)
        print(f"{int(tc)//60}:{int(tc)%60:02d}   {b:5.0f} {r:5.1f} {f:5.1f} {pw:5.1f}")
