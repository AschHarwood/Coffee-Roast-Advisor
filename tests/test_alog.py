"""Unit tests for .alog parsing/decoding against real archive files."""

import glob

import numpy as np
import pytest

from roast_advisor import alog

FILES = sorted(glob.glob("data/raw/training_data/*.alog"))
HOT_COHORT = {"24-03-07_1252.alog", "24-03-11_1616.alog"}


def test_archive_present():
    assert len(FILES) >= 60


def test_dial_decoding_known_values():
    # Artisan stores dial d as d*1.1 + 1 (observed raw values 2.1 .. 10.9)
    for dial in range(1, 10):
        raw = dial * 1.1 + 1
        assert alog.decode_dial(raw) == dial


@pytest.mark.parametrize("path", FILES)
def test_every_file_loads(path):
    r = alog.load_roast(path)
    assert r["mode"] == "F"
    assert len(r["t"]) == len(r["bt"]) == len(r["ror"])
    assert r["drop_t"] > 0
    for te, ty, val in r["events"]:
        assert ty in ("fan", "power")
        assert 0 <= val <= 9


def test_timeindex_marks_decoded():
    # 25-12-24_2052.alog has timeindex [-1, 0, 205, 0, 0, 0, 315, 0]:
    # no CHARGE mark, FCs at sample 205, DROP at sample 315
    r = alog.load_roast("data/raw/training_data/25-12-24_2052.alog")
    assert r["fcs_t"] is not None and r["drop_marked"]
    assert r["fcs_t"] < r["drop_t"]
    assert 350 < r["fcs_bt"] < 430


def test_charge_estimated_from_preheat_plunge():
    # recording starts at ~304F preheat, turning point at raw t=74s ->
    # charge must be detected between those, and TP lands 20-90s after it
    r = alog.load_roast("data/raw/training_data/25-11-18_0743.alog")
    assert r["charge_method"] == "estimated"
    assert 5 < r["charge_raw_t"] < 60
    assert 20 < r["tp_t"] < 90
    assert 100 < r["tp_bt"] < 160


def test_charge_assumed_zero_when_no_preheat_recorded():
    # recording starts mid-plunge at ~189F: no peak to detect
    r = alog.load_roast("data/raw/training_data/25-07-27_1858.alog")
    assert r["charge_method"] == "assumed_zero"
    assert r["charge_raw_t"] == 0.0


def test_hot_probe_cohort_reads_high():
    for name in HOT_COHORT:
        r = alog.load_roast(f"data/raw/training_data/{name}")
        if r["fcs_t"] is not None:
            assert r["fcs_bt"] > 450


def test_ror_is_smooth_and_sane():
    r = alog.load_roast("data/raw/training_data/25-12-24_2052.alog")
    mid = (r["t"] > r["tp_t"] + 30) & (r["t"] < r["fcs_t"])
    ror_mid = r["ror"][mid]
    assert np.nanmedian(ror_mid) > 5
    assert np.nanmax(np.abs(ror_mid)) < 100


def test_setting_at_forward_fills():
    events = [(10.0, "fan", 9), (10.0, "power", 1), (70.0, "power", 3)]
    assert alog.setting_at(events, "power", 60) == 1
    assert alog.setting_at(events, "power", 71) == 3
    assert alog.setting_at(events, "fan", 200) == 9
    assert alog.setting_at(events, "power", 5) is None
