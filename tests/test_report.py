"""Report tests: score a real historical roast against the checked-in target."""

import json

from roast_advisor import alog, report
from roast_advisor.designer import load_target

TARGET = "tests/fixtures/target_city_10min.json"
ROAST = "data/raw/training_data/25-12-24_2052.alog"


def test_profile_score_real_roast():
    target = load_target(TARGET)
    roast = alog.load_roast(ROAST)
    score = report.profile_score(target, roast)

    for name in ("tp", "fcs", "drop"):
        ms = score["milestones"][name]
        assert ms["t"] is not None and ms["dt"] is not None
    # this roast dropped at 10:31 having first-cracked at 6:51 -> DTR ~35%
    assert 0.30 < score["dtr"]["actual"] < 0.40
    assert score["bt_err_mean"] > 0
    assert set(score["by_phase"]) <= {"drying", "maillard", "development"}


def test_advisor_score_counts_consistent(tmp_path):
    target = load_target(TARGET)
    roast = alog.load_roast(ROAST)
    plan = json.loads(open("tests/fixtures/city_10min_dtr22_plan.json").read())
    adv = report.advisor_score(target, plan, roast)
    assert adv["n_recommendations"] == len(adv["changes"])
    assert 0 <= adv["n_applied"] <= adv["n_recommendations"]
    for row in adv["changes"]:
        assert row["applied"] or "deviation_effect" in row


def test_run_writes_all_outputs(tmp_path):
    text, png = report.run(TARGET, ROAST, reports_dir=tmp_path)
    assert "PROFILE ADHERENCE" in text and "ADVISOR ADHERENCE" in text
    stem = "25-12-24_2052_vs_city_10min_dtr22"
    for ext in (".png", ".json", ".txt"):
        assert (tmp_path / f"{stem}{ext}").exists()
    scorecard = json.loads((tmp_path / f"{stem}.json").read_text())
    assert scorecard["profile"]["milestones"]["drop"]["t"] > 0
