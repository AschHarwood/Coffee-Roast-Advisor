"""Command-line entry points: ingest / design / plan / report (all via uv run)."""

import argparse
from pathlib import Path


def ingest_main():
    p = argparse.ArgumentParser(description="Ingest .alog archive into parquet tables")
    p.add_argument("--scan", default="data/raw", help="folder to scan recursively")
    args = p.parse_args()
    from . import ingest

    result = ingest.run(raw_dir=args.scan)
    print(ingest.quality_report(result))
    print("\ntables written to data/ ; per-file detail in data/quality_report.csv")
    print("cohort labels in data/cohort_labels.json — edit and re-run ingest to change")


def design_main():
    p = argparse.ArgumentParser(description="Design a target BT/RoR curve from constraints")
    p.add_argument("--name", required=True)
    p.add_argument("--total", type=float, default=600.0, help="total roast seconds")
    p.add_argument("--dev", type=float, default=None,
                   help="development time in seconds (FC->drop) — the primary "
                        "design variable; overrides --dtr")
    p.add_argument("--dtr", type=float, default=0.22)
    p.add_argument("--fcs-bt", type=float, default=392.0)
    p.add_argument("--drop-bt", type=float, default=406.0)
    p.add_argument("--charge-bt", type=float, default=300.0)
    p.add_argument("--tp", type=float, default=50.0, help="turning point seconds")
    p.add_argument("--tp-bt", type=float, default=140.0)
    p.add_argument("--ror-at-drop", type=float, default=5.0)
    p.add_argument("--shape", choices=["history", "linear"], default="history",
                   help="main-phase RoR shape: measured from your roast history "
                        "(default) or the legacy linear decline")
    args = p.parse_args()
    from . import designer

    ror_shape = None
    if args.shape == "history":
        from . import dataset

        try:
            roasts, samples = dataset.load_tables()
            ror_shape = dataset.median_ror_shape(roasts, samples)
        except FileNotFoundError:
            print("no ingested data found (run: uv run ingest) — using linear shape")

    tgt = designer.design_target(
        args.name, total_s=args.total, dtr=args.dtr, fcs_bt=args.fcs_bt,
        drop_bt=args.drop_bt, charge_bt=args.charge_bt, tp_s=args.tp,
        tp_bt=args.tp_bt, ror_at_drop=args.ror_at_drop, ror_shape=ror_shape,
        dev_time_s=args.dev,
    )
    issues = designer.validate_target(tgt)
    for msg in issues["soft"]:
        print(f"warning: {msg}")
    if issues["hard"]:
        for msg in issues["hard"]:
            print(f"REJECTED: {msg}")
        raise SystemExit(1)
    path = designer.save_target(tgt)
    d = tgt["meta"]["derived"]
    print(f"target written: {path}")
    shape_note = (f"machine shape (peak {d['ror_peak']} F/min)"
                  if "ror_peak" in d else "linear decline")
    print(f"main-phase RoR: {shape_note} -> FCs ({d['fcs_time']}) {d['ror_at_fcs']} "
          f"-> drop {args.ror_at_drop}")


def plan_main():
    p = argparse.ArgumentParser(description="Generate a cue card from a target + roast history")
    p.add_argument("--target", required=True, help="target curve JSON (from design)")
    p.add_argument("--data", default="data", help="folder with ingested parquet tables")
    args = p.parse_args()
    from . import dataset, designer, planner

    target = designer.load_target(args.target)
    roasts, samples = dataset.load_tables(args.data)
    S = dataset.knn_training_samples(roasts, samples)
    n_roasts = len(dataset.included_uuids(roasts))
    plan = planner.make_plan(target, S)
    card = planner.save_plan(target, plan, plans_dir=Path(args.target).parent)
    print(card)
    print(f"\n[kNN over {len(S)} samples from {n_roasts} cohort-consistent roasts]")
    name = target["meta"]["name"]
    print(f"saved: plans/{name}_cue_card.txt, plans/{name}_plan.json, plans/{name}_plan.png")


def report_main():
    p = argparse.ArgumentParser(description="Score a finished roast against target and plan")
    p.add_argument("--target", required=True, help="target curve JSON")
    p.add_argument("--roast", required=True, help=".alog of the finished roast")
    p.add_argument("--plan", default=None, help="plan JSON (default: <target>_plan.json)")
    args = p.parse_args()
    from . import report

    text, png = report.run(args.target, args.roast, plan_path=args.plan)
    print(text)
    print(f"\noverlay plot: {png}")
