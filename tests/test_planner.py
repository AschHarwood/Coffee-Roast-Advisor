"""Designer + planner tests, including the leave-one-out replay acceptance test."""

import json

import numpy as np
import pytest

from roast_advisor import dataset, designer, planner


@pytest.fixture(scope="module")
def tables():
    return dataset.load_tables()


@pytest.fixture(scope="module")
def target():
    return designer.load_target("plans/target_city_10min.json")


def test_designer_reproduces_existing_target():
    # the checked-in target JSON was produced by the validated prototype;
    # the ported designer must rebuild the same curve
    existing = json.loads(open("plans/target_city_10min.json").read())
    rebuilt = designer.design_target("city_10min_dtr22")
    assert rebuilt["meta"]["constraints"] == existing["meta"]["constraints"]
    assert rebuilt["meta"]["derived"]["fcs_s"] == existing["meta"]["derived"]["fcs_s"]
    np.testing.assert_allclose(rebuilt["curve"]["bt"], existing["curve"]["bt"], atol=0.02)


def test_training_matrix_excludes_hot_cohort(tables):
    roasts, samples = tables
    S = dataset.knn_training_samples(roasts, samples)
    assert len(S) > 2000
    # hot-probe roasts read ~484-494F at FCs; without them no sample sits up there
    assert S[:, 0].max() < 470


def test_plan_structure(tables, target):
    roasts, samples = tables
    S = dataset.knn_training_samples(roasts, samples)
    plan = planner.make_plan(target, S)

    opening = [ch for ch in plan["changes"] if ch["t"] == 0]
    assert {(c["setting"], c["value"]) for c in opening} == {("fan", 9), ("power", 1)}
    assert all(
        ch["t"] >= planner.OPENING_END_S for ch in plan["changes"] if ch["t"] > 0
    )
    total = target["meta"]["constraints"]["total_s"]
    assert all(ch["t"] <= total - planner.NO_CHANGE_TAIL_S
               for ch in plan["changes"] if ch["t"] > 0)
    for cp in plan["checkpoints"]:
        assert 1 <= cp["fan"] <= 9 and 1 <= cp["power"] <= 9

    # a nervous, oscillating plan is unusable even if "correct"
    for setting in ("fan", "power"):
        seq = [ch["value"] for ch in plan["changes"] if ch["setting"] == setting]
        deltas = np.diff(seq)
        reversals = sum(1 for a, b in zip(deltas, deltas[1:]) if a * b < 0)
        assert reversals <= 1, f"{setting} plan oscillates: {seq}"


def test_leave_one_out_replay_acceptance(tables):
    """Acceptance test from the brief: replaying each cohort-consistent roast
    against a model trained on the others, recommendations must match the
    operator's actual settings within +/-1 dial step at most checkpoints."""
    roasts, samples = tables
    usable = dataset.included_uuids(roasts)
    per_roast = []
    for u in usable:
        S = dataset.knn_training_samples(roasts, samples, exclude_uuids=[u])
        g = samples[samples["roastUUID"] == u].sort_values("t")
        g = g[g["fan"].notna() & g["power"].notna() & g["ror"].notna()]
        if len(g) < 10:
            continue
        hits_f = hits_p = n = 0
        for tc in np.arange(60, g["t"].max(), 30):
            row = g.iloc[(g["t"] - tc).abs().argmin()]
            if abs(row["t"] - tc) > 5:
                continue
            f, p = planner.predict_settings(S, row["bt"], row["ror"])
            n += 1
            hits_f += abs(round(f) - row["fan"]) <= 1
            hits_p += abs(round(p) - row["power"]) <= 1
        if n >= 5:
            per_roast.append((hits_f / n, hits_p / n))

    assert len(per_roast) >= 40
    fan_rates = [f for f, _ in per_roast]
    pow_rates = [p for _, p in per_roast]
    both_majority = sum(1 for f, p in per_roast if f > 0.5 and p > 0.5)
    assert np.median(fan_rates) >= 0.9
    assert np.median(pow_rates) >= 0.7
    assert both_majority / len(per_roast) >= 0.75


def test_history_shape_target_hits_constraints(tables):
    """A history-shaped target must still land every milestone exactly."""
    import numpy as np

    roasts, samples = tables
    shape = dataset.median_ror_shape(roasts, samples)
    tgt = designer.design_target("shape_test", ror_shape=shape)
    c, con = tgt["curve"], tgt["meta"]["constraints"]
    t = np.asarray(c["t"]); bt = np.asarray(c["bt"])
    ror = np.asarray([np.nan if v is None else v for v in c["ror"]])
    fcs_s = tgt["meta"]["derived"]["fcs_s"]

    assert abs(np.interp(fcs_s, t, bt) - con["fcs_bt"]) < 1.0
    assert abs(bt[-1] - con["drop_bt"]) < 1.0
    # continuous RoR across the FCs boundary (no step in the target)
    i = np.searchsorted(t, fcs_s)
    assert abs(ror[i + 1] - ror[i - 1]) < 2.0
    # shape sanity: near-zero at TP, violent rebound, declining tail
    main = (t > con["tp_s"]) & (t <= fcs_s)
    assert ror[main][0] < 25
    assert 60 < np.nanmax(ror[main]) < 160
    assert ror[main][-1] < 15
    assert np.all(ror[main] >= 0)


def test_history_shape_matches_real_roast_better(tables):
    """The redesigned curve must fit the first advised roast's RoR far better
    than the legacy linear target through the mid-roast (2:00-6:00).
    (Margin is modest: that roast was steered toward the linear target.)"""
    import numpy as np
    from roast_advisor import alog

    roasts, samples = tables
    shape = dataset.median_ror_shape(roasts, samples)
    linear = designer.design_target("lin")
    shaped = designer.design_target("shp", ror_shape=shape)
    r = alog.load_roast("data/raw/training_data/first_roast.alog")

    m = (r["t"] >= 120) & (r["t"] <= 360) & (r["bt"] > 0)
    ts = r["t"][m]

    def err(tgt):
        c = tgt["curve"]
        ok = [v is not None for v in c["ror"]]
        tt = np.asarray(c["t"])[ok]
        rr = np.asarray([v for v in c["ror"] if v is not None])
        return float(np.nanmean(np.abs(r["ror"][m] - np.interp(ts, tt, rr))))

    assert err(shaped) < err(linear)


def test_validate_target_passes_good_designs(tables):
    roasts, samples = tables
    shape = dataset.median_ror_shape(roasts, samples)
    for tgt in (designer.design_target("ok_lin"),
                designer.design_target("ok_shape", ror_shape=shape),
                designer.design_target("ok_dev", ror_shape=shape, dev_time_s=105)):
        issues = designer.validate_target(tgt)
        assert issues["hard"] == [], issues


def test_validate_target_rejects_underdevelopment():
    tgt = designer.design_target("bad_dev", dev_time_s=40)
    issues = designer.validate_target(tgt)
    assert any("under-development" in m for m in issues["hard"])


def test_validate_target_warns_low_drop_ror():
    tgt = designer.design_target("low_ror", ror_at_drop=2.0)
    issues = designer.validate_target(tgt)
    assert any("drop RoR" in m for m in issues["soft"])


def test_dev_time_is_primary_over_dtr():
    tgt = designer.design_target("dev_primary", total_s=600, dtr=0.22, dev_time_s=90)
    assert tgt["meta"]["derived"]["fcs_s"] == 510.0
    assert abs(tgt["meta"]["constraints"]["dtr"] - 0.15) < 1e-9
