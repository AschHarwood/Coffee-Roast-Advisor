import ast, glob, os

def load(p):
    return ast.literal_eval(open(p).read())

def fmt_t(s):
    m,sec=divmod(int(round(s)),60); return f"{m}:{sec:02d}"

files = sorted(glob.glob('/sessions/confident-trusting-curie/mnt/uploads/*.alog'))
for p in files:
    d = load(p)
    name = os.path.basename(p).split('-',5)[-1]
    timex, bt, et = d['timex'], d['temp2'], d['temp1']
    ti = d['timeindex']  # [CHARGE, DRY, FCs, FCe, SCs, SCe, DROP, COOL]
    charge = timex[ti[0]] if ti[0]>-1 else 0
    print('='*70)
    print(f"FILE: {os.path.basename(p)[37:]}")
    print(f"  title={d.get('title')!r} date={d.get('roastisodate')} mode={d.get('mode')} samples={len(timex)} interval={d.get('samplinginterval')}s")
    print(f"  beans={d.get('beans')!r}")
    print(f"  weight={d.get('weight')} ambient={d.get('ambientTemp')} humidity={d.get('ambient_humidity')}")
    print(f"  etypes={d.get('etypes')}")
    marks=['CHARGE','DRY','FCs','FCe','SCs','SCe','DROP','COOL']
    for i,m in enumerate(marks):
        if i<len(ti) and ti[i]>0:
            t=timex[ti[i]]-charge
            print(f"    {m:6s} {fmt_t(t)}  BT={bt[ti[i]]:.1f}  ET={et[ti[i]]:.1f}")
    se=d.get('specialevents',[]); st=d.get('specialeventstype',[]); sv=d.get('specialeventsvalue',[]); ss=d.get('specialeventsStrings',[])
    print(f"  events: {len(se)}")
    for idx,ty,val,s in zip(se,st,sv,ss):
        t=timex[idx]-charge
        etype = d['etypes'][ty] if ty < len(d['etypes']) else ty
        # artisan stores slider value as v/10+1
        print(f"    {fmt_t(t):>6s}  {etype:12s} val={(val-1)*10:.0f}  str={s!r}  BT={bt[idx]:.1f}")
