import ast, glob, os
import numpy as np

def load(p): return ast.literal_eval(open(p).read())
def get_roast(p):
    d=load(p)
    t=np.array(d['timex']); bt=np.array(d['temp2'])
    etypes=[e.lower() for e in d['etypes']]
    ev=sorted(zip(d['specialevents'],d['specialeventstype'],d['specialeventsvalue']))
    events=[(t[i], etypes[ty], round((v-1)*10/11)) for i,ty,v in ev]
    P=np.full(len(t),np.nan); F=np.full(len(t),np.nan); curP=curF=None; j=0
    for i in range(len(t)):
        while j<len(events) and events[j][0]<=t[i]:
            _,ty,val=events[j]
            if ty=='power': curP=val
            elif ty=='fan': curF=val
            j+=1
        P[i]=curP if curP is not None else np.nan
        F[i]=curF if curF is not None else np.nan
    ti=d['timeindex']; drop=ti[6] if len(ti)>6 and ti[6]>0 else len(t)-1
    return dict(name=os.path.basename(p)[37:], t=t, bt=bt, P=P, F=F, drop=drop)

files=sorted(glob.glob('/sessions/confident-trusting-curie/mnt/uploads/*.alog'))
roasts=[get_roast(p) for p in files]
# keep the 5 consistent roasts (exclude the two 2024-03 hot-probe ones)
keep=[r for r in roasts if '24-03' not in r['name']]
print("using:", [r['name'][:30] for r in keep])

def build(rs):
    X=[];Y=[]
    for r in rs:
        t,bt,P,F=r['t'],r['bt'],r['P'],r['F']
        for i in range(len(t)):
            if np.isnan(P[i]) or np.isnan(F[i]) or bt[i]<150: continue
            if t[i]>t[r['drop']]: break
            m=(t>=t[i]-10)&(t<=t[i]+10)
            if m.sum()<4: continue
            X.append([1,P[i],F[i],bt[i]]); Y.append(np.polyfit(t[m],bt[m],1)[0])
    return np.array(X),np.array(Y)

X,Y=build(keep)
coef,_,_,_=np.linalg.lstsq(X,Y,rcond=None)
pred=X@coef; r2=1-np.sum((Y-pred)**2)/np.sum((Y-np.mean(Y))**2)
c0,c1,c2,c3=coef
print(f"n={len(Y)}  RoR[F/min] = {c0*60:.1f} {c1*60:+.2f}*P {c2*60:+.2f}*F {c3*60:+.3f}*BT   R^2={r2:.3f}")

# leave-one-out: predict required power at checkpoints for each held-out roast
print("\nLeave-one-out validation (model-recommended power vs what you actually set):")
allerr=[]
for hold in keep:
    train=[r for r in keep if r is not hold]
    Xt,Yt=build(train)
    h,_,_,_=np.linalg.lstsq(Xt,Yt,rcond=None)
    t,bt,P,F=hold['t'],hold['bt'],hold['P'],hold['F']
    errs=[]
    rows=[]
    for tc in range(150,int(t[hold['drop']]),45):
        i=np.searchsorted(t,tc)
        if i>=len(t) or np.isnan(P[i]): continue
        m=(t>=tc-15)&(t<=tc+15)
        ror=np.polyfit(t[m],bt[m],1)[0]
        needP=(ror-h[0]-h[2]*F[i]-h[3]*bt[i])/h[1]
        errs.append(needP-P[i]); rows.append((tc,bt[i],ror*60,F[i],P[i],needP))
    mae=np.mean(np.abs(errs))
    allerr+=errs
    print(f"\n  {hold['name'][:40]}  MAE={mae:.1f} power units")
    for tc,b,r_,f,p,np_ in rows:
        print(f"    {tc//60}:{tc%60:02d}  BT={b:3.0f}  RoR={r_:5.1f}  F={f:.0f}  actual P={p:.0f}  model P={np_:4.1f}")
print(f"\nOverall MAE: {np.mean(np.abs(allerr)):.2f} power units (dial is 1-9)")
