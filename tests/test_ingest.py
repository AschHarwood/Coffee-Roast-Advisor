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
    assert len(result["failed"]) == 0
    assert len(result["roasts"]) == result["n_files"]
    assert result["roasts"]["roastUUID"].is_unique


def test_hot_probe_cohort_auto_excluded(result):
    roasts = result["roasts"]
    excluded = set(roasts.loc[roasts["exclude"], "file"])
    assert HOT_COHORT_FILES <= excluded
    # and nothing in the main cohort got swept up with them
    flagged_hot = set(roasts.loc[roasts["cohort"] == "hot_probe", "file"])
    assert flagged_hot == HOT_COHORT_FILES


def test_samples_have_settings_and_phases(result):
    s = result["samples"]
    assert {"roastUUID", "t", "bt", "ror", "fan", "power", "phase"} <= set(s.columns)
    assert set(s["phase"].unique()) <= {"drying", "maillard", "development"}
    # forward-filled settings exist for the bulk of mid-roast samples
    mid = s[(s["t"] > 90)]
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
    assert "usable for kNN planning" in text
    for f in HOT_COHORT_FILES:
        assert f in text
