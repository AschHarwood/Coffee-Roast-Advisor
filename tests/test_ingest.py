"""Ingest pipeline tests: full-archive run, idempotency, cohort flagging."""

import pandas as pd
import pytest

from roast_advisor import ingest

HOT_COHORT_FILES = {"24-03-07_1252.alog", "24-03-11_1616.alog"}


@pytest.fixture(scope="module")
def tmp_data(tmp_path_factory, monkeypatch_module=None):
    return tmp_path_factory.mktemp("data")


@pytest.fixture(scope="module")
def result(tmp_data, module_mocker=None):
    # run against the real archive but write parquet to a temp dir
    import roast_advisor.ingest as ing

    orig = ing.DATA_DIR
    ing.DATA_DIR = tmp_data
    try:
        yield ing.run(raw_dir="data/raw", data_dir=tmp_data)
    finally:
        ing.DATA_DIR = orig


def test_all_files_ingested(result):
    assert result["n_files"] >= 62  # the archive grows with every roast
    # the author's own sr800 archive must always parse cleanly; external
    # community files may legitimately be rejected (empty/aborted recordings)
    sr_files = {p.name for p in __import__("pathlib").Path("data/raw/training_data").glob("*.alog")}
    assert not [f for f, _ in result["failed"] if f in sr_files]
    sr = result["roasts"][result["roasts"]["machine"] == "sr800"]
    assert len(sr) >= 62
    accounted = len(result["roasts"]) + len(result["failed"]) + len(result["skipped"])
    assert accounted == result["n_files"]
    assert result["roasts"]["roastUUID"].is_unique


def test_hot_probe_cohort_auto_excluded(result):
    roasts = result["roasts"]
    excluded = set(roasts.loc[roasts["exclude"], "file"])
    assert HOT_COHORT_FILES <= excluded
    # and nothing else in the sr800 cohort got swept up with them
    sr = roasts[roasts["machine"] == "sr800"]
    flagged_hot = set(sr.loc[sr["cohort"] == "hot_probe", "file"])
    assert flagged_hot == HOT_COHORT_FILES


def test_samples_have_settings_and_phases(result):
    s = result["samples"]
    assert {"roastUUID", "t", "bt", "ror", "fan", "power", "phase"} <= set(s.columns)
    assert set(s["phase"].unique()) <= {"drying", "maillard", "development"}
    # forward-filled settings exist for the bulk of the author's mid-roast
    # samples (external archives may have event-less roasts)
    roasts = result["roasts"]
    sr_ids = roasts.loc[roasts["machine"] == "sr800", "roastUUID"]
    mid = s[(s["t"] > 90) & s["roastUUID"].isin(sr_ids)]
    assert mid["power"].notna().mean() > 0.7


def test_rerun_is_idempotent(tmp_data, result):
    import roast_advisor.ingest as ing

    orig = ing.DATA_DIR
    ing.DATA_DIR = tmp_data
    try:
        again = ing.run(raw_dir="data/raw", data_dir=tmp_data)
    finally:
        ing.DATA_DIR = orig
    for key in ("roasts", "samples", "events"):
        assert len(again[key]) == len(result[key]), key
    assert again["roasts"]["roastUUID"].is_unique


def test_quality_report_renders(result):
    text = ingest.quality_report(result)
    assert "usable for sr800 kNN planning" in text
    for f in HOT_COHORT_FILES:
        assert f in text
