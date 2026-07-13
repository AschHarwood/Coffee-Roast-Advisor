"""Live bridge: owns the meter's serial port, feeds Artisan over WebSocket,
and prints cue-card recommendations to the terminal during the roast.

    uv run live --target plans/target_city_10min.json [--port /dev/cu.SLAB_USBtoUART]

Artisan setup (once): Config -> Device -> WebSocket, host 127.0.0.1 port 8765,
data request command "getData", channel 1 node "BT". Artisan then records
through the bridge exactly as it used to record from the serial port.

Design rules (from the project brief):
- deterministic: no model calls at roast time; the advisor only reads the
  plan JSON + target JSON produced offline
- each planned change announced ~10s early, then at its due time
- off-plan corrections printed distinctly (ADJUST), rate-limited
- stale serial data must fail loudly, never silently
"""

import argparse
import asyncio
import contextlib
import json
import sys
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np

from .ms6514 import FrameStream, decode_frame
from .planner import fmt

ROR_WINDOW_S = 20.0            # trailing regression window for live RoR
LEAD_S = 10.0                  # announce planned changes this early
ADJUST_COOLDOWN_S = 30.0       # min seconds between off-plan corrections
STALE_S = 5.0                  # no serial data for this long -> alarm

BT_GAIN = 15.0                 # projected deg F of BT error worth one power step
LOOKAHEAD_S = 90.0             # judge the error where the roast is HEADING:
                               # projected_err = bt_err + ror_err * lookahead.
                               # "+6F hot but RoR 9 low" is not fine — it is
                               # about to be 8F cold, and that must fire a cue.
DROP_WARN_LOOKAHEAD_S = 30.0   # warn when BT will reach drop temp this soon


# ---------------------------------------------------------------- pure logic

# THE charge rule lives in alog.py so offline and live timelines always agree
from .alog import (  # noqa: E402  (re-exported for callers and tests)
    CHARGE_MIN_PREHEAT_F,
    CHARGE_MIN_DROP_F,
    CHARGE_MIN_RATE_F_S,
    detect_charge,
)


def live_ror(samples, now, window=ROR_WINDOW_S):
    """F/min from a trailing regression window (live: no future samples)."""
    pts = [(t, b) for t, b in samples if now - window <= t <= now]
    if len(pts) < 4:
        return None
    t = np.array([p[0] for p in pts])
    b = np.array([p[1] for p in pts])
    return float(np.polyfit(t, b, 1)[0] * 60)


class Advisor:
    """Deterministic cue engine: plan schedule + deviation corrections.

    Feed it (t, bt, ror) ticks; it returns the lines to print. Pure logic —
    no clocks, no IO — so replay and live runs produce identical output.
    """

    def __init__(self, target, plan):
        self.target = target
        self.plan = plan
        c = target["curve"]
        self._tgt_t = np.asarray(c["t"], dtype=float)
        self._tgt_bt = np.asarray(c["bt"], dtype=float)
        ok = ~np.isnan(np.asarray(c["ror"], dtype=float))
        self._ror_t = self._tgt_t[ok]
        self._tgt_ror = np.asarray(c["ror"], dtype=float)[ok]
        self.schedule = sorted(
            (ch for ch in plan["changes"] if ch["t"] > 0), key=lambda ch: ch["t"]
        )
        self._announced = set()
        self._done = set()
        self._last_adjust_t = -1e9
        self._drop_warned = False
        self._drop_called = False
        self.total_s = target["meta"]["constraints"]["total_s"]
        self.drop_bt = target["meta"]["constraints"]["drop_bt"]

    def target_at(self, t):
        return (
            float(np.interp(t, self._tgt_t, self._tgt_bt)),
            float(np.interp(t, self._ror_t, self._tgt_ror)),
        )

    def planned_setting(self, kind, t):
        v = self.plan["opening"][kind]
        for ch in self.schedule:
            if ch["setting"] == kind and ch["t"] <= t:
                v = ch["value"]
        return v

    def tick(self, t, bt, ror):
        """One advisor step -> (announcement_lines, status_line)."""
        lines = []
        opening_end = self.plan["opening"]["until_s"]
        for i, ch in enumerate(self.schedule):
            label = f"{ch['setting'].capitalize()} -> {ch['value']}"
            if i not in self._announced and ch["t"] - LEAD_S <= t < ch["t"]:
                self._announced.add(i)
                lines.append(f"UPCOMING ({fmt(ch['t'])}): {label}")
            if i not in self._done and t >= ch["t"]:
                self._announced.add(i)
                self._done.add(i)
                lines.append(f"NOW: {label}")

        tgt_bt, tgt_ror = self.target_at(t)
        bt_err = bt - tgt_bt
        ror_err = (ror - tgt_ror) if ror is not None else 0.0

        # drop watch: the one cue that must never be missed. Fires on actual
        # BT relative to the drop temp, regardless of what the clock says.
        if not self._drop_called and t > self.total_s * 0.6:
            projected = bt + (ror or 0.0) * DROP_WARN_LOOKAHEAD_S / 60
            if bt >= self.drop_bt:
                self._drop_called = True
                dt = t - self.total_s
                timing = f"{fmt(abs(dt))} {'late' if dt > 0 else 'early'} vs plan"
                lines.append(
                    f"DROP NOW: BT {bt:.0f} (target {self.drop_bt:.0f}, {timing})"
                )
            elif not self._drop_warned and projected >= self.drop_bt:
                self._drop_warned = True
                lines.append(
                    f"DROP WINDOW: BT {bt:.0f}, reaching {self.drop_bt:.0f} in "
                    f"~{DROP_WARN_LOOKAHEAD_S:.0f}s"
                )

        if (
            t >= opening_end
            and t <= self.total_s
            and t - self._last_adjust_t >= ADJUST_COOLDOWN_S
        ):
            plan_p = self.planned_setting("power", t)
            # projected error: where the roast is heading, not where it is —
            # opposing BT/RoR errors must not cancel into silence
            projected_err = bt_err + ror_err * LOOKAHEAD_S / 60
            corr = -projected_err / BT_GAIN
            # one step at a time: a calm advisor beats a "correct" nervous one
            rec = int(np.clip(plan_p + np.sign(corr), 1, 9)) if abs(corr) >= 0.5 else plan_p
            if rec != plan_p:
                self._last_adjust_t = t
                why = []
                if abs(bt_err) >= 3:
                    why.append(f"{abs(bt_err):.0f}F {'hot' if bt_err > 0 else 'cold'}")
                if abs(ror_err) >= 2:
                    why.append(f"RoR {ror_err:+.0f}")
                reason = "running " + ", ".join(why) if why else "drifting off plan"
                lines.append(f"ADJUST: Power -> {rec} ({reason})")

        if t < opening_end:
            status = (
                f"{fmt(t)} | BT {bt:.0f} | opening block F{self.plan['opening']['fan']}"
                f"/P{self.plan['opening']['power']} | first change at {fmt(opening_end)}"
            )
        else:
            on = "ON PLAN" if abs(bt_err) < 4 and abs(ror_err) < 3 else (
                f"{'HOT' if bt_err > 0 else 'COLD'} {abs(bt_err):.0f}F"
            )
            ror_s = f"{ror:.1f}" if ror is not None else "--"
            status = (
                f"{fmt(t)} | BT {bt:.0f} (tgt {tgt_bt:.0f}, {bt_err:+.0f}F) | "
                f"RoR {ror_s} (tgt {tgt_ror:.1f}) | "
                f"plan F{self.planned_setting('fan', t)}/P{self.planned_setting('power', t)} | {on}"
            )
        return lines, status


def replay_advisor(target, plan, t, bt, tick_s=2.0):
    """Run the Advisor over a recorded (t, bt) series; returns the transcript.

    This is the Stage 5 determinism reference: the live stack replaying the
    same roast must print exactly these lines.
    """
    adv = Advisor(target, plan)
    samples = deque()
    transcript = []
    ok = bt > 0
    t, bt = t[ok], bt[ok]
    for tc in np.arange(max(t[0], 0.0), min(t[-1], adv.total_s + 60), tick_s):
        b = float(np.interp(tc, t, bt))
        samples.append((tc, b))
        while samples[0][0] < tc - 60:
            samples.popleft()
        lines, _ = adv.tick(tc, b, live_ror(samples, tc))
        transcript.extend(f"[{fmt(tc)}] {line}" for line in lines)
    return transcript


# ---------------------------------------------------------------- live wiring

class MeterReader(threading.Thread):
    """Reads the serial port; keeps (wall_t, bt) history and staleness info."""

    def __init__(self, port, baud=9600):
        super().__init__(daemon=True)
        self.port, self.baud = port, baud
        self.samples = deque(maxlen=600)  # ~5 min at 2 Hz
        self.last_data_t = None
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()

    def run(self):
        import serial

        stream = FrameStream()
        while not self.stop_flag.is_set():
            try:
                with serial.Serial(self.port, self.baud, timeout=0.5) as ser:
                    while not self.stop_flag.is_set():
                        chunk = ser.read(64)
                        if not chunk:
                            continue
                        for frame in stream.feed(chunk):
                            bean, _ = decode_frame(frame)
                            if bean is not None:
                                with self.lock:
                                    self.samples.append((time.monotonic(), bean))
                                    self.last_data_t = time.monotonic()
            except Exception as e:
                print(f"\nSERIAL ERROR: {e} — retrying in 2s", file=sys.stderr)
                time.sleep(2)

    def snapshot(self):
        with self.lock:
            return list(self.samples), self.last_data_t


async def websocket_server(reader, state, host, port):
    import websockets

    async def handler(ws):
        state["clients"].add(ws)
        try:
            async for msg in ws:
                try:
                    req = json.loads(msg)
                except json.JSONDecodeError:
                    continue
                samples, last = reader.snapshot()
                stale = last is None or time.monotonic() - last > STALE_S
                data = {} if stale else {"BT": samples[-1][1], "ET": -1}
                await ws.send(json.dumps({"id": req.get("id", 0), "data": data}))
        finally:
            state["clients"].discard(ws)

    return await websockets.serve(handler, host, port)


async def push_message(state, message):
    """Unsolicited event to Artisan; node name and values match the defaults in
    Artisan's Config -> Port -> WebSocket dialog (Message node 'pushMessage',
    CHARGE message 'startRoasting')."""
    import websockets

    for ws in list(state["clients"]):
        with contextlib.suppress(websockets.ConnectionClosed):
            await ws.send(json.dumps({"pushMessage": message}))


async def live_loop(reader, advisor, state, push_charge):
    charge_wall_t = None
    last_status = 0.0
    alarmed = False
    while True:
        await asyncio.sleep(0.5)
        now = time.monotonic()
        samples, last = reader.snapshot()

        if last is not None and now - last > STALE_S:
            if not alarmed:
                print(f"\n!!! NO METER DATA for {STALE_S:.0f}s — check USB/meter. "
                      "Artisan is being told nothing (no stale readings). !!!")
                alarmed = True
            continue
        alarmed = False
        if not samples:
            continue

        bt = samples[-1][1]
        if charge_wall_t is None:
            det = detect_charge([(t, b) for t, b in samples if t >= now - 60])
            if det is not None:
                charge_wall_t = det
                print(f"\n*** CHARGE detected (BT plunge from preheat) — t=0 ***")
                if push_charge:
                    await push_message(state, "startRoasting")
            elif now - last_status >= 2:
                last_status = now
                print(f"\rwaiting for charge | BT {bt:.0f}F", end="", flush=True)
            continue

        t = now - charge_wall_t
        rel = [(wt - charge_wall_t, b) for wt, b in samples]
        lines, status = advisor.tick(t, bt, live_ror(rel, t))
        for line in lines:
            print(f"\n{line}")
        if now - last_status >= 2:
            last_status = now
            print(f"\r{status}", end="", flush=True)
        if t > advisor.total_s + 120:
            print("\npast target drop +2min — bridge exiting (save your roast in Artisan)")
            return


def live_main():
    p = argparse.ArgumentParser(description="Serial->Artisan bridge with live advisor")
    p.add_argument("--target", required=True, help="target curve JSON")
    p.add_argument("--plan", default=None, help="plan JSON (default: <name>_plan.json)")
    p.add_argument("--port", default="/dev/cu.SLAB_USBtoUART")
    p.add_argument("--baud", type=int, default=9600)
    p.add_argument("--ws-host", default="127.0.0.1")
    p.add_argument("--ws-port", type=int, default=8765)
    p.add_argument("--push-charge", action="store_true",
                   help="also mark CHARGE in Artisan when detected")
    args = p.parse_args()

    from .designer import load_target

    target = load_target(args.target)
    plan_path = args.plan or Path(args.target).parent / f"{target['meta']['name']}_plan.json"
    plan = json.loads(Path(plan_path).read_text())
    advisor = Advisor(target, plan)

    reader = MeterReader(args.port, args.baud)
    reader.start()
    state = {"clients": set()}

    print(f"bridge up: meter {args.port} -> ws://{args.ws_host}:{args.ws_port}")
    print(f"plan: {plan_path} ({len(advisor.schedule)} changes)  "
          f"opening F{plan['opening']['fan']}/P{plan['opening']['power']} until "
          f"{fmt(plan['opening']['until_s'])}")
    print("in Artisan: Config -> Device -> WebSocket, then ON. charge auto-detects.\n")

    async def main():
        server = await websocket_server(reader, state, args.ws_host, args.ws_port)
        try:
            await live_loop(reader, advisor, state, args.push_charge)
        finally:
            server.close()
            reader.stop_flag.set()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbridge stopped")


def replay_main():
    p = argparse.ArgumentParser(description="Offline advisor replay over a recorded roast")
    p.add_argument("--target", required=True)
    p.add_argument("--roast", required=True)
    p.add_argument("--plan", default=None)
    args = p.parse_args()

    from .alog import load_roast
    from .designer import load_target

    target = load_target(args.target)
    plan_path = args.plan or Path(args.target).parent / f"{target['meta']['name']}_plan.json"
    plan = json.loads(Path(plan_path).read_text())
    roast = load_roast(args.roast)
    for line in replay_advisor(target, plan, roast["t"], roast["bt"]):
        print(line)
