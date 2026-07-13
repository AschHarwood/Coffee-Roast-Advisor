"""Load the parquet tables and produce the kNN training matrix."""

from pathlib import Path

import numpy as np
import pandas as pd

KNN_STEP_S = 10.0   # sample the history every 10s, as validated in the prototype
KNN_T_MIN = 40.0    # skip the first 40s: pre-TP data is noisy and never planned over


def load_tables(data_dir="data"):
    data_dir = Path(data_dir)
    roasts = pd.read_parquet(data_dir / "roasts.parquet")
    samples = pd.read_parquet(data_dir / "samples.parquet")
    return roasts, samples


def included_uuids(roasts, exclude_uuids=(), machine="sr800"):
    ok = roasts[
        (~roasts["exclude"]) & (roasts["n_events"] > 0)
        & (roasts["machine"] == machine)
    ]
    return [u for u in ok["roastUUID"] if u not in set(exclude_uuids)]


def median_ror_shape(roasts, samples, n_points=41):
    """Median normalized RoR profile over the main phase (TP -> FCs).

    Each cohort-consistent roast's RoR is sampled on a normalized time grid
    u = (t - tp) / (fcs - tp) and divided by its own mean, so the median
    captures the SHAPE of how this machine's probe RoR evolves (violent
    post-TP rebound, steep decay) independent of each roast's level.
    Returns (u_grid, shape); shape is clipped non-negative at the TP end.
    """
    ok = roasts[
        (~roasts["exclude"]) & roasts["fcs_t"].notna() & roasts["tp_t"].notna()
        & (roasts["machine"] == "sr800")
    ]
    u_grid = np.linspace(0, 1, n_points)
    profiles = []
    for _, r in ok.iterrows():
        if r["fcs_t"] - r["tp_t"] < 120:
            continue
        g = samples[samples["roastUUID"] == r["roastUUID"]].sort_values("t")
        g = g[g["ror"].notna()]
        u = (g["t"].values - r["tp_t"]) / (r["fcs_t"] - r["tp_t"])
        m = (u >= 0) & (u <= 1)
        if m.sum() < 20:
            continue
        prof = np.interp(u_grid, u[m], g["ror"].values[m])
        if prof.mean() > 5:
            profiles.append(prof / prof.mean())
    shape = np.median(np.array(profiles), axis=0)
    return u_grid, np.clip(shape, 0, None)


def knn_training_samples(roasts, samples, exclude_uuids=(), machine="sr800"):
    """(BT, RoR, fan, power) rows from cohort-consistent roasts, every 10s.

    Single-machine by design: settings semantics don't transfer across
    machine classes. exclude_uuids additionally holds out roasts (LOO replay).
    """
    keep = samples[
        samples["roastUUID"].isin(included_uuids(roasts, exclude_uuids, machine))
    ]
    rows = []
    for _, g in keep.groupby("roastUUID"):
        g = g.sort_values("t")
        tics = np.arange(KNN_T_MIN, g["t"].max(), KNN_STEP_S)
        idx = np.searchsorted(g["t"].values, tics)
        idx = np.clip(idx, 0, len(g) - 1)
        sub = g.iloc[idx]
        sub = sub[sub["fan"].notna() & sub["power"].notna() & sub["ror"].notna()]
        rows.append(sub[["bt", "ror", "fan", "power"]])
    out = pd.concat(rows, ignore_index=True)
    return out.to_numpy(dtype=float)
