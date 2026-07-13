import ast, glob, os
import numpy as np

def load(p): return ast.literal_eval(open(p).read())

def smooth_ror(timex, bt, win=15):
    """RoR in F/min via centered linear fit over +-win seconds."""
    t=np.array(timex); b=np.array(bt); ror=np.full(len(t), np.nan)
    for i in range(len(t)):
        m=(t>=t[i]-win)&(t<=t[i]+win)
        if m.sum()>=3:
            ror[i]=np.polyfit(t[m],b[m],1)[0]*60
    return ror

files = sorted(glob.glob('/sessions/confident-trusting-curie/mnt/uploads/*.alog'))
steps=[]
for p in files:
    d=load(p)
    t=np.array(d['timex']); bt=np.array(d['temp2'])
    ror=smooth_ror(t,bt)
    # reconstruct power & fan settings over time
    ev=list(zip(d['specialevents'],d['specialeventstype'],d['specialeventsvalue']))
    etypes=[e.lower() for e in d['etypes']]
    # power steps: find power events where power changed and no other power change within next 60s
    pw=[(t[i], round((v-1)*10/11)) for i,ty,v in ev if etypes[ty]=='power']
    fn=[(t[i], round((v-1)*10/11)) for i,ty,v in ev if etypes[ty]=='fan']
    for k in range(1,len(pw)):
        t0,newp=pw[k]; oldp=pw[k-1][1]
        dp=newp-oldp
        if dp==0: continue
        # exclude if another power change within 70s after
        if k+1<len(pw) and pw[k+1][0]-t0<70: continue
        # fan change at same moment?
        fan_change = any(abs(tf-t0)<15 for tf,_ in fn[1:] if any(abs(tf-tfp)<1e-9 for tfp,_ in fn))
        df=0
        prevf=None; curf=None
        for tf,fv in fn:
            if tf<=t0+10: 
                if tf < t0-10: prevf=fv
                else: curf=fv
        if prevf is not None and curf is not None: df=curf-prevf
        # RoR before (avg -30..-5s) and after (+30..+70s)
        mb=(t>=t0-30)&(t<=t0-5); ma=(t>=t0+30)&(t<=t0+70)
        if mb.sum()<3 or ma.sum()<3: continue
        rb=np.nanmean(ror[mb]); ra=np.nanmean(ror[ma])
        steps.append(dict(file=os.path.basename(p)[37:57], t=t0, dp=dp, df=df, bt=bt[np.searchsorted(t,t0)], ror_before=rb, ror_after=ra, dror=ra-rb))

print(f"{'roast':22s} {'t':>5s} {'BT':>5s} {'dPower':>6s} {'dFan':>4s} {'RoR pre':>8s} {'RoR post':>8s} {'dRoR':>6s} {'dRoR/dP':>7s}")
for s in steps:
    print(f"{s['file']:22s} {s['t']:5.0f} {s['bt']:5.0f} {s['dp']:+6d} {s['df']:+4d} {s['ror_before']:8.1f} {s['ror_after']:8.1f} {s['dror']:+6.1f} {s['dror']/s['dp']:+7.1f}")

clean=[s for s in steps if s['df']==0]
arr=np.array([s['dror']/s['dp'] for s in steps])
print(f"\nAll steps: n={len(steps)}, median dRoR per power unit = {np.median(arr):+.1f} F/min")
arr2=np.array([s['dror']/s['dp'] for s in clean])
if len(clean): print(f"Power-only steps: n={len(clean)}, median = {np.median(arr2):+.1f} F/min per power unit")

# lag estimate: cross-correlate RoR change onset after big power steps
print("\nLag check on large steps (|dP|>=2):")
for p in files:
    d=load(p)
    t=np.array(d['timex']); bt=np.array(d['temp2']); ror=smooth_ror(t,bt)
    ev=list(zip(d['specialevents'],d['specialeventstype'],d['specialeventsvalue']))
    etypes=[e.lower() for e in d['etypes']]
    pw=[(t[i], round((v-1)*10/11)) for i,ty,v in ev if etypes[ty]=='power']
    for k in range(1,len(pw)):
        t0,newp=pw[k]; dp=newp-pw[k-1][1]
        if abs(dp)<2: continue
        i0=np.searchsorted(t,t0)
        base=np.nanmean(ror[max(0,i0-8):i0])
        # find first time RoR moves >30% of eventual change in direction of dp
        m=(t>t0)&(t<=t0+90)
        seg=ror[m]; ts=t[m]
        target=np.nanmean(ror[(t>=t0+40)&(t<=t0+80)])
        if np.isnan(target) or abs(target-base)<1: continue
        thr=base+0.3*(target-base)
        cross=[tt-t0 for tt,r in zip(ts,seg) if (r>thr if target>base else r<thr)]
        if cross: print(f"  {os.path.basename(p)[37:57]:22s} t={t0:5.0f}s dP={dp:+d}: RoR responds in ~{cross[0]:.0f}s (base {base:.0f}→{target:.0f} F/min)")
