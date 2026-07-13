"""Stage 2: a fake MS6514 the bridge cannot distinguish from real hardware.

Replays either a raw capture (.jsonl from `uv run capture`) or a historical
roast (.alog, BT synthesized into meter frames at 2 Hz) onto a pty. The
bridge opens the pty path exactly as it would open the real serial port.

    uv run fakemeter --alog data/raw/training_data/25-12-24_2052.alog
    -> prints the pty path to give the bridge via --port

--speed N runs the clock N times faster (a 10-minute roast tests in seconds).
"""

import argparse
import os
import time

import numpy as np

from .ms6514 import FRAME_LEN, SIGNATURE, TRAILER, read_capture

# constants observed in every real frame from this meter (bytes 2-4, 9-10, 13)
_FILL_2_4 = bytes([0x00, 0x00, 0x00])
_FILL_9_10 = bytes([0x01, 0x82])
_NC_SECONDARY = 0x109D  # garbage value the meter sends for the open channel


def encode_frame(bean_f, timer_ticks=0):
    """BT reading -> an 18-byte frame identical in shape to the real meter's.

    Mirrors this user's meter config: bean probe on the main display
    (status 0x09), second channel not connected (status 0x40).
    """
    main = max(0, min(0xFFFF, int(round(bean_f * 10))))
    frame = bytearray(FRAME_LEN)
    frame[0:2] = SIGNATURE
    frame[2:5] = _FILL_2_4
    frame[5] = main >> 8
    frame[6] = main & 0xFF
    frame[7] = _NC_SECONDARY >> 8
    frame[8] = _NC_SECONDARY & 0xFF
    frame[9:11] = _FILL_9_10
    frame[11] = 0x09
    frame[12] = 0x40
    frame[13] = 0x00
    frame[14] = (timer_ticks >> 8) & 0xFF
    frame[15] = timer_ticks & 0xFF
    frame[16:18] = TRAILER
    return bytes(frame)


def alog_schedule(path, hz=2.0):
    """(t, frame) pairs replaying a historical roast's BT at the meter's rate."""
    from .alog import parse_alog_file

    d = parse_alog_file(path)
    t = np.asarray(d["timex"], dtype=float)
    bt = np.asarray(d["temp2"], dtype=float)
    ok = bt > 0
    out = []
    ticks = 0
    for tc in np.arange(t[0], t[-1], 1.0 / hz):
        ticks += 3  # the real meter's byte-14/15 counter advances ~5/s
        out.append((float(tc - t[0]), encode_frame(float(np.interp(tc, t[ok], bt[ok])), ticks)))
    return out


def capture_schedule(path):
    """(t, raw_bytes) pairs replaying a capture file byte-for-byte."""
    return read_capture(path)


def serve_pty(schedule, speed=1.0, on_ready=None, master_fd=None, start_delay=0.5):
    """Write the schedule onto a pty; returns after the last byte is sent.

    start_delay gives the consumer time to open the slave side before the
    first frame is written (bytes written before it opens are dropped).
    """
    if master_fd is None:
        master_fd, slave_fd = os.openpty()
        if on_ready:
            on_ready(os.ttyname(slave_fd))
    time.sleep(start_delay)
    start = time.monotonic()
    for t, data in schedule:
        due = start + t / speed
        delay = due - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        os.write(master_fd, data)


def fakemeter_main():
    p = argparse.ArgumentParser(description="Replay a capture or .alog as a live meter")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--alog", help="historical roast to replay (BT -> frames)")
    src.add_argument("--capture", help="raw capture .jsonl to replay byte-for-byte")
    p.add_argument("--speed", type=float, default=1.0, help="clock multiplier")
    args = p.parse_args()

    schedule = alog_schedule(args.alog) if args.alog else capture_schedule(args.capture)
    total = schedule[-1][0] / args.speed

    def announce(path):
        print(f"fake meter running on: {path}")
        print(f"point the bridge at it:  uv run live --port {path} ...")
        print(f"replaying {schedule[-1][0]:.0f}s of data at {args.speed}x "
              f"({total:.0f}s wall clock), Ctrl-C to stop")

    try:
        serve_pty(schedule, speed=args.speed, on_ready=announce)
        print("replay finished")
    except KeyboardInterrupt:
        print("\nstopped")
