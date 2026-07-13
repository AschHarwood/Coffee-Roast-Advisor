"""Scan .alog archive into parquet tables, idempotently, with a data-quality report.

Tables (keyed by roastUUID):
- data/roasts.parquet   one row per roast: metadata, milestones, quality flags
- data/samples.parquet  one row per 2s sample: t, bt, et, ror, fan, power, phase
- data/events.parquet   one row per fan/power slider move

Cohort handling: roasts whose FCs BT sits >30F from the archive median are
flagged as a suspected probe cohort and excluded from modeling by default.
Overrides live in data/cohort_labels.json (edit by hand, re-run ingest).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import alog

DATA_DIR = Path("data")
COHORT_OUTLIER_F = 30.0


def scan_files(raw_dir):
    return sorted(Path(raw_dir).rglob("*.alog"))


def machine_tag(path, raw_dir):
    """Machine class from folder layout: training_data/ is the author's sr800;
    external/<source>/ and community/<handle>/ are tagged by that folder name."""
    try:
        parts = Path(path).relative_to(raw_dir).parts
    except ValueError:
        return "unknown"
    if parts[0] == "training_data":
        return "sr800"
    if parts[0] in ("external", "community") and len(parts) > 2:
        return parts[1]
    return parts[0] if len(parts) > 1 else "unknown"


def roast_row(r, machine="sr800"):
    total = r["drop_t"]
    dtr = (total - r["fcs_t"]) / total if r["fcs_t"] and total else None
    t = r["t"]
    interval = float(np.median(np.diff(t))) if len(t) > 1 else None
    return {
        "roastUUID": r["uuid"],
        "file": Path(r["path"]).name,
        "date": r["date"],
        "epoch": r["epoch"],
        "title": r["title"],
        "beans": r["beans"],
        "weight_in_g": r["weight_in_g"],
        "weight_out_g": r["weight_out_g"],
        "ambient_temp": r["ambient_temp"],
        "ambient_humidity": r["ambient_humidity"],
        "machine": machine,
        "charge_method": r["charge_method"],
        "tp_t": r["tp_t"],
        "tp_bt": r["tp_bt"],
        "dry_t": r["dry_t"],
        "fcs_t": r["fcs_t"],
        "fcs_bt": r["fcs_bt"],
        "drop_t": r["drop_t"],
        "drop_bt": r["drop_bt"],
        "drop_marked": r["drop_marked"],
        "dtr": dtr,
        "total_s": total,
        "sample_interval_s": interval,
        "n_events": len(r["events"]),
        "n_samples": int(len(t)),
    }


def sample_rows(r):
    t, bt, et, ror = r["t"], r["bt"], r["et"], r["ror"]
    keep = (t >= 0) & (t <= r["drop_t"]) & (bt > 0)
    rows = pd.DataFrame(
        {
            "roastUUID": r["uuid"],
            "t": t[keep],
            "bt": bt[keep],
            "et": et[keep],
            "ror": ror[keep],
        }
    )
    fan = [alog.setting_at(r["events"], "fan", tc) for tc in rows["t"]]
    power = [alog.setting_at(r["events"], "power", tc) for tc in rows["t"]]
    rows["fan"] = pd.array(fan, dtype="Int64")
    rows["power"] = pd.array(power, dtype="Int64")
    rows["phase"] = [alog.phase_of(tc, r["fcs_t"], r["dry_t"]) for tc in rows["t"]]
    return rows


def event_rows(r):
    return pd.DataFrame(
        [
            {"roastUUID": r["uuid"], "t": te, "type": ty, "value": val}
            for te, ty, val in r["events"]
        ]
    )


def flag_cohorts(roasts, labels_path=DATA_DIR / "cohort_labels.json"):
    """Add exclude/cohort columns; suspected outliers excluded unless overridden."""
    # probe frames differ by machine: outliers are judged against the
    # median of the SAME machine class, and only where the class has enough
    # marked roasts for a stable median
    med = roasts.groupby("machine")["fcs_bt"].transform("median")
    n_marked = roasts.groupby("machine")["fcs_bt"].transform("count")
    suspected = ((roasts["fcs_bt"] - med).abs() > COHORT_OUTLIER_F) & (n_marked >= 5)
    suspected = suspected.fillna(False)

    labels = {}
    if labels_path.exists():
        labels = json.loads(labels_path.read_text())

    cohort, exclude, reason = [], [], []
    for _, row in roasts.iterrows():
        lab = labels.get(row["roastUUID"], {})
        is_suspect = bool(suspected.loc[row.name])
        cohort.append(lab.get("cohort", "hot_probe" if is_suspect else "main"))
        if "exclude" in lab:
            exclude.append(bool(lab["exclude"]))
            reason.append(lab.get("reason", "user label"))
        elif is_suspect:
            exclude.append(True)
            reason.append(
                f"suspected probe cohort: FCs BT {row['fcs_bt']:.0f}F vs "
                f"{row['machine']} median {med.loc[row.name]:.0f}F"
            )
        else:
            exclude.append(False)
            reason.append("")
    roasts = roasts.copy()
    roasts["cohort"] = cohort
    roasts["exclude"] = exclude
    roasts["exclude_reason"] = reason

    if not labels_path.exists():
        seed = {
            row["roastUUID"]: {
                "file": row["file"],
                "cohort": row["cohort"],
                "exclude": bool(row["exclude"]),
                "reason": row["exclude_reason"],
            }
            for _, row in roasts.iterrows()
            if row["exclude"]
        }
        labels_path.write_text(json.dumps(seed, indent=1))
    return roasts


def upsert(new, path, key="roastUUID"):
    """Replace rows for UUIDs present in `new`, keep everything else."""
    if Path(path).exists():
        old = pd.read_parquet(path)
        old = old[~old[key].isin(new[key].unique())]
        new = pd.concat([old, new], ignore_index=True)
    new.to_parquet(path, index=False)
    return new


def run(raw_dir="data/raw", data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    data_dir.mkdir(exist_ok=True)
    files = scan_files(raw_dir)
    parsed, failed, skipped = [], [], []
    seen_uuids = set()
    all_samples, all_events = [], []
    for path in files:
        try:
            r = alog.load_roast(path)
            if r["uuid"] in seen_uuids:
                skipped.append((path.name, "duplicate roastUUID (same roast, another file)"))
                continue
            seen_uuids.add(r["uuid"])
            r["_machine"] = machine_tag(path, raw_dir)
            parsed.append(r)
            all_samples.append(sample_rows(r))
            ev = event_rows(r)
            if len(ev):
                all_events.append(ev)
        except Exception as e:  # a corrupt file must not sink the whole ingest
            failed.append((path.name, f"{type(e).__name__}: {e}"))

    roasts = pd.DataFrame([roast_row(r, r["_machine"]) for r in parsed])
    roasts = flag_cohorts(roasts, data_dir / "cohort_labels.json")
    roasts = upsert(roasts, data_dir / "roasts.parquet")
    samples = upsert(pd.concat(all_samples, ignore_index=True), data_dir / "samples.parquet")
    events = upsert(pd.concat(all_events, ignore_index=True), data_dir / "events.parquet")
    return {
        "roasts": roasts,
        "samples": samples,
        "events": events,
        "failed": failed,
        "skipped": skipped,
        "n_files": len(files),
    }


def quality_report(result):
    """Printable per-file data-quality report; also saved as CSV."""
    roasts = result["roasts"].sort_values("epoch", na_position="first")
    lines = []
    lines.append(
        f"INGEST: {result['n_files']} files scanned, "
        f"{len(roasts)} roasts in dataset, {len(result['failed'])} rejected, "
        f"{len(result.get('skipped', []))} duplicates skipped"
    )
    for name, err in result["failed"]:
        lines.append(f"  REJECTED: {name}: {err}")
    for name, why in result.get("skipped", []):
        lines.append(f"  SKIPPED: {name}: {why}")
    by_machine = roasts.groupby("machine")["fcs_bt"].median()
    lines.append("FCs BT median by machine (F, outliers judged within machine): "
                 + ", ".join(f"{m}={v:.0f}" for m, v in by_machine.dropna().items()))
    lines.append("")
    hdr = (f"{'file':<48} {'machine':<22} {'date':<10} {'charge':<12} "
           f"{'FCs':>7} {'DROP':>7} {'ev':>3} {'cohort':<9} excluded")
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for _, r in roasts.iterrows():
        fcs = f"{r['fcs_bt']:.0f}F" if pd.notna(r["fcs_bt"]) else "-"
        drop = "-" if not r["drop_marked"] else f"{r['drop_t']/60:.1f}m"
        excl = f"YES: {r['exclude_reason']}" if r["exclude"] else ""
        lines.append(
            f"{r['file']:<48} {r['machine']:<22} {str(r['date'])[:10]:<10} "
            f"{r['charge_method']:<12} {fcs:>7} {drop:>7} {r['n_events']:>3} "
            f"{r['cohort']:<9} {excl}"
        )
    lines.append("")
    n = len(roasts)
    lines.append("SUMMARY")
    lines.append(f"  charge marked / estimated / assumed t=0: "
                 f"{(roasts['charge_method']=='marked').sum()} / "
                 f"{(roasts['charge_method']=='estimated').sum()} / "
                 f"{(roasts['charge_method']=='assumed_zero').sum()}  (of {n})")
    lines.append(f"  missing DROP mark: {(~roasts['drop_marked']).sum()}")
    lines.append(f"  missing FCs mark:  {roasts['fcs_bt'].isna().sum()}")
    lines.append(f"  no fan/power events (unusable for planning): {(roasts['n_events']==0).sum()}")
    lines.append(f"  excluded from modeling: {roasts['exclude'].sum()} "
                 f"({', '.join(roasts.loc[roasts['exclude'],'file'])})")
    lines.append("  roasts by machine: " + ", ".join(
        f"{m}={n}" for m, n in roasts["machine"].value_counts().items()))
    sr = roasts[roasts["machine"] == "sr800"]
    lines.append(f"  usable for sr800 kNN planning: "
                 f"{((~sr['exclude']) & (sr['n_events']>0)).sum()}")
    report = "\n".join(lines)
    csv_path = DATA_DIR / "quality_report.csv"
    roasts.to_csv(csv_path, index=False)
    return report
