"""Design a Rao-compliant target curve: city roast, 10:00, FCs 392F @ 22% DTR, drop 406F."""
import json, csv
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

# constraints
TOTAL   = 600.0          # 10:00
DTR     = 0.22           # Rao: 20-25%
FCS_BT  = 392.0
DROP_BT = 406.0
CHARGE_BT = 300.0        # preheat, probe reading at charge
TP_T, TP_BT = 50.0, 140.0
R_END   = 5.0            # RoR at drop (Rao: don't go below ~5)

FCS_T = TOTAL*(1-DTR)                      # 468s = 7:48
DEV_MIN = (TOTAL-FCS_T)/60                 # 2.2 min
# development: linear RoR R1 -> R_END integrating to (406-392)
R1 = 2*(DROP_BT-FCS_BT)/DEV_MIN - R_END    # RoR at FCs
# main: linear RoR R0 -> R1 integrating to (392-140)
MAIN_MIN = (FCS_T-TP_T)/60
R0 = 2*(FCS_BT-TP_BT)/MAIN_MIN - R1        # RoR at TP

def ror(t):
    if t < TP_T: return None
    if t <= FCS_T: return R0 + (R1-R0)*(t-TP_T)/(FCS_T-TP_T)
    return R1 + (R_END-R1)*(t-FCS_T)/(TOTAL-FCS_T)

# build BT curve at 2s (pre-TP: cosmetic quadratic descent 300->140, zero slope at TP)
ts=np.arange(0,TOTAL+1,2.0)
bt=[]
b=TP_BT
for t in ts:
    if t<=TP_T:
        u=t/TP_T; bt.append(CHARGE_BT+(TP_BT-CHARGE_BT)*(2*u-u*u))
    else:
        b=bt[-1]+ror(t-2)*2/60 if bt else TP_BT
        bt.append(bt[int(TP_T//2)] if t==TP_T else b)
# recompute cleanly by integration from TP
bt=np.array(bt)
i_tp=int(TP_T//2)
for i in range(i_tp+1,len(ts)):
    bt[i]=bt[i-1]+(ror(ts[i-1])+ror(ts[i]))/2*2/60

def fmt(s): m,x=divmod(int(round(s)),60); return f"{m}:{x:02d}"
meta=dict(
    name="city_10min_dtr22",
    description="City roast target. Rao-style continuously declining RoR.",
    units="F, seconds from charge",
    constraints=dict(total_s=TOTAL, dtr=DTR, fcs_bt=FCS_BT, drop_bt=DROP_BT,
                     charge_bt=CHARGE_BT, tp_s=TP_T, tp_bt=TP_BT, ror_at_drop=R_END),
    derived=dict(fcs_s=FCS_T, fcs_time=fmt(FCS_T), ror_at_tp=round(R0,1),
                 ror_at_fcs=round(R1,1), dev_time_min=round(DEV_MIN,2)),
    compare_from_s=TP_T,  # pre-TP segment is cosmetic; score comparisons from TP onward
)
out=dict(meta=meta,
         curve=dict(t=[float(t) for t in ts],
                    bt=[round(float(v),2) for v in bt],
                    ror=[round(ror(t),2) if ror(t) is not None else None for t in ts]))
json.dump(out,open('target_city_10min.json','w'),indent=1)
with open('target_city_10min.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['t_sec','bt_F','ror_F_per_min'])
    for t,b_ in zip(ts,bt): w.writerow([t,round(b_,2),round(ror(t),2) if ror(t) is not None else ''])

print(f"RoR at TP: {R0:.1f} F/min -> at FCs ({fmt(FCS_T)}): {R1:.1f} -> at DROP (10:00): {R_END:.1f}")
print(f"Check: BT at FCs {bt[np.searchsorted(ts,FCS_T)]:.1f}F, at drop {bt[-1]:.1f}F, DTR {DTR:.0%}, dev {DEV_MIN:.1f} min")

# ---- chart ----
fig,(ax1,ax2)=plt.subplots(2,1,figsize=(11,8),sharex=True,gridspec_kw={'height_ratios':[3,2]})
tm=ts/60
ax1.plot(tm,bt,'b-',lw=2.5,label='Target BT')
ax1.axvspan(TP_T/60,4.7,color='gold',alpha=.08); ax1.axvspan(4.7,FCS_T/60,color='orange',alpha=.08); ax1.axvspan(FCS_T/60,10,color='brown',alpha=.10)
ax1.text(2.5,410,'drying',color='goldenrod',ha='center'); ax1.text(6.2,410,'maillard',color='darkorange',ha='center'); ax1.text(8.9,410,'development\n(DTR 22%)',color='brown',ha='center',fontsize=9)
for tt,bb,lab in [(TP_T/60,TP_BT,f'TP {fmt(TP_T)} @140F'),(FCS_T/60,FCS_BT,f'FCs {fmt(FCS_T)} @392F'),(10,DROP_BT,'DROP 10:00 @406F')]:
    ax1.plot([tt],[bb],'ko',ms=6); ax1.annotate(lab,(tt,bb),textcoords='offset points',xytext=(8,-14),fontsize=9)
ax1.set_ylabel('Bean temp (F)'); ax1.set_ylim(120,440); ax1.grid(alpha=.3); ax1.legend(loc='center right')
ax1.set_title('City roast target — 10:00 total, FCs 392F @ 7:48 (22% DTR), drop 406F')
rr=[ror(t) for t in ts]
ax2.plot(tm,[r if r is not None else np.nan for r in rr],'r-',lw=2.5,label='Target RoR')
ax2.axhline(5,color='gray',ls=':',lw=1); ax2.text(0.2,5.5,'Rao floor ~5 F/min',fontsize=8,color='gray')
ax2.axvline(FCS_T/60,color='brown',ls=':',alpha=.6)
ax2.annotate(f'{R0:.0f}',(TP_T/60,R0),textcoords='offset points',xytext=(6,4),color='r')
ax2.annotate(f'{R1:.1f}',(FCS_T/60,R1),textcoords='offset points',xytext=(6,6),color='r')
ax2.set_ylabel('RoR (F/min)'); ax2.set_xlabel('Minutes from charge'); ax2.set_ylim(0,72); ax2.grid(alpha=.3); ax2.legend()
plt.tight_layout(); plt.savefig('target_city_10min.png',dpi=110)
print("files: target_city_10min.json / .csv / .png")
