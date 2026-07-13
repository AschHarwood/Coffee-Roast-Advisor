"""Bridge tests: fake meter round-trip, charge detection acceptance,
advisor scheduling/corrections/determinism, WebSocket format."""

import asyncio
import glob
import json
import threading
import time

import numpy as np
import pytest

from roast_advisor import alog, fakemeter, live
from roast_advisor.designer import load_target
from roast_advisor.ms6514 import FrameStream, decode_frame

TARGET = "tests/fixtures/target_city_10min.json"
PLAN = "tests/fixtures/city_10min_dtr22_plan.json"


# ------------------------------------------------------------- fake meter

def test_encode_decode_roundtrip():
    for temp in (32.0, 78.3, 212.0, 393.7, 485.5):
        bean, second = decode_frame(fakemeter.encode_frame(temp))
        assert bean == pytest.approx(temp, abs=0.05)
        assert second is None  # mimics this setup: no second probe


def test_pty_replay_reaches_bridge_byte_perfect():
    schedule = fakemeter.alog_schedule("data/raw/training_data/25-12-24_2052.alog")[:120]
    expected = [decode_frame(f)[0] for _, f in schedule]

    path_holder = {}
    ready = threading.Event()

    def on_ready(path):
        path_holder["path"] = path
        ready.set()

    t = threading.Thread(
        target=fakemeter.serve_pty, args=(schedule,), kwargs={"speed": 60, "on_ready": on_ready}
    )
    t.start()
    assert ready.wait(5)
    reader = live.MeterReader(path_holder["path"])
    reader.start()
    t.join(timeout=10)
    time.sleep(0.5)  # let the reader drain the pty
    reader.stop_flag.set()
    samples, last = reader.snapshot()
    got = [b for _, b in samples]
    assert last is not None
    assert got == expected  # pty is lossless: byte-perfect through the real reader


# ------------------------------------------------------- charge detection

def _stream_detect(t, bt):
    """Feed samples in order; return (detected_charge_t, detection_fired_at)."""
    window = []
    for tc, b in zip(t, bt):
        if b <= 0:
            continue
        window.append((tc, b))
        window = [(x, y) for x, y in window if x >= tc - 60]
        det = live.detect_charge(window)
        if det is not None:
            return det, tc
    return None, None


# the archive only contains 2 usable preheat-visible recordings:
# 26-01-14_2057.alog is excluded because a 6s probe dropout swallowed its
# entire plunge — the true charge time is unknowable from that file.
REAL_PREHEAT_FILES = ["25-11-18_0743.alog", "25-12-09_1749.alog"]
MID_PLUNGE_FILES = [  # recordings that start partway down the charge plunge
    "25-07-27_1858.alog",
    "25-09-03_1717.alog",
    "25-11-26_2009.alog",
    "25-12-09_1804.alog",
]


def test_charge_detection_acceptance():
    """Brief checklist: detection within 5s of charge on >=5 replayed roasts.

    Only 2 archive recordings contain the full preheat plunge, so the rest
    are reconstructed: a realistic ~300F preheat plateau spliced onto real
    mid-plunge recordings (charge time known by construction). The pure
    all-real version of this criterion completes at the Stage 4 bench test.
    """
    cases = []
    for name in REAL_PREHEAT_FILES:
        r = alog.load_roast(f"data/raw/training_data/{name}")
        d = alog.parse_alog_file(f"data/raw/training_data/{name}")
        cases.append((name, r["charge_raw_t"],
                      np.asarray(d["timex"], float), np.asarray(d["temp2"], float)))
    rng = np.random.default_rng(7)
    for name in MID_PLUNGE_FILES:
        d = alog.parse_alog_file(f"data/raw/training_data/{name}")
        t = np.asarray(d["timex"], float)
        bt = np.asarray(d["temp2"], float)
        # 60s of noisy plateau, then a ~2s/sample ramp down into the recording
        plateau_t = np.arange(0, 60, 2.0)
        plateau = 300 + rng.normal(0, 0.4, len(plateau_t))
        ramp_bt = np.linspace(300, bt[0], 6)[1:-1]
        ramp_t = 60 + 2.0 * np.arange(1, len(ramp_bt) + 1)
        offset = ramp_t[-1] + 2.0 - t[0]
        cases.append((f"synthetic:{name}", 60.0,
                      np.concatenate([plateau_t, ramp_t, t + offset]),
                      np.concatenate([plateau, ramp_bt, bt])))

    assert len(cases) >= 5
    misses = []
    for name, ref, t_raw, bt_raw in cases:
        det, fired_at = _stream_detect(t_raw, bt_raw)
        if det is None or abs(det - ref) > 5:
            misses.append((name, ref, det))
    assert not misses, f"detections off by >5s: {misses}"


def test_no_false_charge_at_room_temp():
    t = np.arange(0, 120, 0.5)
    bt = 78 + np.random.default_rng(0).normal(0, 0.2, len(t))
    det, _ = _stream_detect(t, bt)
    assert det is None


def test_no_false_charge_during_preheat_climb():
    # rising toward preheat must never look like a charge (only a plunge does)
    t = np.arange(0, 90, 0.5)
    bt = np.linspace(210, 307, len(t))
    det, _ = _stream_detect(t, bt)
    assert det is None


# --------------------------------------------------------------- advisor

@pytest.fixture(scope="module")
def target():
    return load_target(TARGET)


@pytest.fixture(scope="module")
def plan():
    return json.loads(open(PLAN).read())


def test_advisor_announces_each_change_early_then_now(target, plan):
    adv = live.Advisor(target, plan)
    lines_all = []
    tgt = adv.target_at
    for tc in np.arange(0, 620, 2.0):
        bt, ror = tgt(tc)
        lines, status = adv.tick(tc, bt, ror)
        lines_all.extend((tc, l) for l in lines)
        assert status
    for ch in adv.schedule:
        label = f"{ch['setting'].capitalize()} -> {ch['value']}"
        ups = [tc for tc, l in lines_all if l == f"UPCOMING ({live.fmt(ch['t'])}): {label}"]
        nows = [tc for tc, l in lines_all if l == f"NOW: {label}" and abs(tc - ch["t"]) <= 2]
        assert len(ups) == 1 and ch["t"] - 10 <= ups[0] < ch["t"], (ch, ups)
        assert len(nows) == 1, (ch, nows)
    # perfectly on-curve: no corrections
    assert not [l for _, l in lines_all if l.startswith("ADJUST")]


def test_advisor_adjusts_when_hot(target, plan):
    # at 5:00 the plan holds power 9 (can't go higher), so test the hot side
    adv = live.Advisor(target, plan)
    tc = 300.0
    tgt_bt, tgt_ror = adv.target_at(tc)
    lines, status = adv.tick(tc, tgt_bt + 15, tgt_ror + 5)
    plan_p = adv.planned_setting("power", tc)
    assert plan_p == 9
    assert any(l.startswith(f"ADJUST: Power -> {plan_p - 1} (running 15F hot") for l in lines)
    assert "HOT 15F" in status


def test_advisor_adjusts_when_cold_with_headroom(target, plan):
    # early ramp (power 4 planned around 2:30): cold -> recommend one step up
    adv = live.Advisor(target, plan)
    tc = 155.0
    tgt_bt, tgt_ror = adv.target_at(tc)
    plan_p = adv.planned_setting("power", tc)
    assert plan_p < 9
    lines, status = adv.tick(tc, tgt_bt - 15, tgt_ror - 5)
    assert any(l.startswith(f"ADJUST: Power -> {plan_p + 1} (running 15F cold") for l in lines)
    assert "COLD 15F" in status


def test_advisor_adjust_rate_limited(target, plan):
    adv = live.Advisor(target, plan)
    n_adjust = 0
    for tc in np.arange(200, 260, 2.0):  # a full minute of running hot
        tgt_bt, tgt_ror = adv.target_at(tc)
        lines, _ = adv.tick(tc, tgt_bt + 20, tgt_ror + 6)
        n_adjust += sum(l.startswith("ADJUST") for l in lines)
    assert n_adjust <= 3  # cooldown keeps it calm, not nagging every tick


def test_replay_is_deterministic(target, plan):
    r = alog.load_roast("data/raw/training_data/25-12-24_2052.alog")
    t1 = live.replay_advisor(target, plan, r["t"], r["bt"])
    t2 = live.replay_advisor(target, plan, r["t"], r["bt"])
    assert t1 == t2
    assert any("NOW:" in l for l in t1)


# -------------------------------------------------------------- websocket

class _StubReader:
    def __init__(self, bt=321.5, stale=False):
        now = time.monotonic()
        self._samples = [(now - 1, bt - 0.5), (now, bt)]
        self._last = None if stale else now

    def snapshot(self):
        return self._samples, self._last


def _ws_roundtrip(reader):
    async def go():
        import websockets

        state = {"clients": set()}
        server = await live.websocket_server(reader, state, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            await ws.send(json.dumps({"command": "getData", "id": 4711, "machine": 0}))
            resp = json.loads(await asyncio.wait_for(ws.recv(), 5))
        server.close()
        await server.wait_closed()
        return resp

    return asyncio.run(go())


def test_websocket_getdata_format():
    resp = _ws_roundtrip(_StubReader(bt=321.5))
    assert resp["id"] == 4711
    assert resp["data"]["BT"] == 321.5
    assert resp["data"]["ET"] == -1


def test_websocket_goes_silent_when_stale():
    # stale serial data must not reach Artisan as if it were fresh
    resp = _ws_roundtrip(_StubReader(stale=True))
    assert resp["id"] == 4711
    assert resp["data"] == {}


# ------------------------------------------------------------- stage 5

def test_live_path_transcript_identical_to_offline_replay(target, plan):
    """Stage 5: the live pipeline (raw samples -> charge detection -> advisor)
    must print exactly what the offline replay tool prints for the same roast.
    Uses a preheat-visible roast so charge detection runs for real."""
    path = "data/raw/training_data/25-11-18_0743.alog"

    offline = live.replay_advisor(*(target, plan), *(lambda r: (r["t"], r["bt"]))(alog.load_roast(path)))

    # live-style: raw uncharged stream, detect charge, then tick the advisor
    d = alog.parse_alog_file(path)
    t_raw = np.asarray(d["timex"], float)
    bt_raw = np.asarray(d["temp2"], float)
    ok = bt_raw > 0
    t_raw, bt_raw = t_raw[ok], bt_raw[ok]

    charge, _ = _stream_detect(t_raw, bt_raw)
    assert charge is not None

    adv = live.Advisor(target, plan)
    from collections import deque
    samples = deque()
    transcript = []
    for tc in np.arange(0.0, min(t_raw[-1] - charge, adv.total_s + 60), 2.0):
        b = float(np.interp(tc + charge, t_raw, bt_raw))
        samples.append((tc, b))
        while samples[0][0] < tc - 60:
            samples.popleft()
        lines, _ = adv.tick(tc, b, live.live_ror(samples, tc))
        transcript.extend(f"[{live.fmt(tc)}] {line}" for line in lines)

    assert transcript == offline
    assert any("NOW:" in l for l in transcript)


def test_advisor_fires_when_opposing_errors_project_cold(target, plan):
    # regression from the first advised roast, 3:59: +6F hot but RoR 9 low.
    # The old 50/50 blend cancelled to silence; projected 90s ahead it is
    # ~8F cold and must recommend one power step up.
    adv = live.Advisor(target, plan)
    tc = 239.0  # plan power is 8 here (9 comes at 4:00)
    plan_p = adv.planned_setting("power", tc)
    assert plan_p == 8
    tgt_bt, tgt_ror = adv.target_at(tc)
    lines, _ = adv.tick(tc, tgt_bt + 6, tgt_ror - 9)
    assert any(l.startswith(f"ADJUST: Power -> {plan_p + 1}") for l in lines)


def test_drop_watch_warns_then_calls(target, plan):
    adv = live.Advisor(target, plan)
    drop_bt = target["meta"]["constraints"]["drop_bt"]
    # late in the roast, closing on drop temp fast -> warning first
    lines, _ = adv.tick(540.0, drop_bt - 6, 12.0)
    assert any(l.startswith("DROP WINDOW") for l in lines)
    # at the temp -> the call, exactly once
    lines, _ = adv.tick(560.0, drop_bt + 0.2, 6.0)
    assert any(l.startswith("DROP NOW") for l in lines)
    lines, _ = adv.tick(562.0, drop_bt + 1, 6.0)
    assert not any(l.startswith("DROP") for l in lines)


def test_drop_watch_silent_early_and_on_curve(target, plan):
    adv = live.Advisor(target, plan)
    out = []
    for tc in np.arange(0, 620, 2.0):
        bt, ror = adv.target_at(tc)
        lines, _ = adv.tick(tc, bt, ror)
        out += lines
    # riding the curve perfectly: drop cue arrives, but only near the end
    drops = [l for l in out if l.startswith("DROP")]
    assert drops and all("DROP" not in l for l in out[: len(out) // 2])
