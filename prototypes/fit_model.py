import ast, glob, os
import numpy as np

def load(p): return ast.literal_eval(open(p).read())

def get_roast(p):
    d=load(p)
    t=np.array(d['timex']); bt=np.array(d['temp2'])
    etypes=[e.lower() for e in d['etypes']]
    ev=sorted(zip(d['specialevents'],d['specialeventstype'],d['specialeventsvalue']))
    P=np.full(len(t),np.nan); F=np.full(len(t),np.nan)
    curP=curF=None
    j=0
    events=[(t[i], etypes[ty], round((v-1)*10/11)) for i,ty,v in ev]
    for i in range(len(t)):
        while j<len(events) and events[j][0]<=t[i]:
            _,ty,val=events[j]
            if ty=='power': curP=val
            elif ty=='fan': curF=val
            j+=1
        P[i]=curP if curP is not None else np.nan
        F[i]=curF if curF is not None else np.nan
    ti=d['timeindex']
    drop = ti[6] if len(ti)>6 and ti[6]>0 else len(t)-1
    return dict(name=os.path.basename(p)[37:], t=t, bt=bt, P=P, F=F, drop=drop, d=d)

files=sorted(glob.glob('/sessions/confident-trusting-curie/mnt/uploads/*.alog'))
roasts=[get_roast(p) for p in files]

# build regression: dBT/dt = c0 + c1*P + c2*F + c3*BT  (per-second)
X=[];Y=[]
for r in roasts:
    t,bt,P,F=r['t'],r['bt'],r['P'],r['F']
    # smooth bt derivative over 20s
    for i in range(len(t)):
        if np.isnan(P[i]) or np.isnan(F[i]): continue
        if t[i]>t[r['drop']]: break
        m=(t>=t[i]-10)&(t<=t[i]+10)
        if m.sum()<4: continue
        dbdt=np.polyfit(t[m],bt[m],1)[0]
        if bt[i]<150: continue  # skip pre-charge chaos
        X.append([1,P[i],F[i],bt[i]]); Y.append(dbdt)
X=np.array(X);Y=np.array(Y)
coef,res,_,_=np.linalg.lstsq(X,Y,rcond=None)
pred=X@coef
ss=1-np.sum((Y-pred)**2)/np.sum((Y-np.mean(Y))**2)
c0,c1,c2,c3=coef
print(f"n={len(Y)} samples pooled from {len(roasts)} roasts")
print(f"dBT/dt [F/s] = {c0:.4f} + {c1:.4f}*Power + {c2:.4f}*Fan + {c3:.5f}*BT   R^2={ss:.3f}")
print(f"In F/min: RoR = {c0*60:.1f} + {c1*60:.2f}*P + {c2*60:.2f}*F {c3*60:+.3f}*BT")
print(f"=> each power step adds ~{c1*60:.1f} F/min RoR; each fan step {c2*60:+.1f} F/min; RoR naturally decays {-c3*60:.2f} F/min per degree BT")

# implied equilibrium temp per (P,F)
print("\nImplied equilibrium BT (where RoR=0):")
for Pv in [3,5,7,9]:
    for Fv in [7,9]:
        eq=-(c0+c1*Pv+c2*Fv)/c3
        print(f"  P={Pv} F={Fv}: {eq:.0f}F", end='')
    print()

# holdout validation: refit without last roast, predict its needed power
hold=roasts[-1]  # 25-09-03
Xh=[];Yh=[]
for r in roasts[:-1]:
    t,bt,P,F=r['t'],r['bt'],r['P'],r['F']
    for i in range(len(t)):
        if np.isnan(P[i]) or np.isnan(F[i]) or bt[i]<150: continue
        if t[i]>t[r['drop']]: break
        m=(t>=t[i]-10)&(t<=t[i]+10)
        if m.sum()<4: continue
        Xh.append([1,P[i],F[i],bt[i]]); Yh.append(np.polyfit(t[m],bt[m],1)[0])
ch,_,_,_=np.linalg.lstsq(np.array(Xh),np.array(Yh),rcond=None)
h0,h1,h2,h3=ch
t,bt,P,F=hold['t'],hold['bt'],hold['P'],hold['F']
print(f"\nHoldout ({hold['name']}): required power to achieve its actual RoR, vs power actually used")
print(f"{'time':>6s} {'BT':>5s} {'actual RoR':>10s} {'fan':>4s} {'P actual':>8s} {'P model':>8s}")
for tc in range(120,int(t[hold['drop']]),60):
    i=np.searchsorted(t,tc)
    if np.isnan(P[i]): continue
    m=(t>=tc-15)&(t<=tc+15)
    ror=np.polyfit(t[m],bt[m],1)[0]
    needP=(ror-h0-h2*F[i]-h3*bt[i])/h1
    print(f"{tc//60}:{tc%60:02d}   {bt[i]:5.0f} {ror*60:10.1f} {F[i]:4.0f} {P[i]:8.0f} {needP:8.1f}")
