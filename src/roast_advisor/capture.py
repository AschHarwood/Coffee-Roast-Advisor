"""Stage 0 of the bridge verification plan: capture raw meter bytes to a file.

Dumps everything the Mastech MS6514 sends over serial, with timestamps, so the
protocol decoder can be written and unit-tested offline against ground truth
(the temps you write down from the meter's LCD during the capture).

Artisan must be CLOSED while this runs — only one program can own the port.
"""

import argparse
import glob
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import serial

DEFAULT_PORT = "/dev/cu.SLAB_USBtoUART"
DEFAULT_BAUD = 9600


def capture_main():
    p = argparse.ArgumentParser(description="Record raw serial bytes from the meter")
    p.add_argument("--port", default=DEFAULT_PORT)
    p.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    p.add_argument("--seconds", type=float, default=120)
    p.add_argument("--out", default="tests/fixtures")
    args = p.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, bytesize=8, parity="N",
                            stopbits=1, timeout=0.2)
    except serial.SerialException as e:
        print(f"could not open {args.port}: {e}\n", file=sys.stderr)
        candidates = sorted(glob.glob("/dev/cu.*"))
        print("serial ports on this machine:", file=sys.stderr)
        for c in candidates:
            print(f"  {c}", file=sys.stderr)
        print("\nif the right port is listed, re-run with --port <it>.", file=sys.stderr)
        print("if Artisan is open, close it first — it holds the port.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"ms6514_capture_{stamp}.jsonl"

    print(f"capturing {args.port} @ {args.baud} baud for {args.seconds:.0f}s -> {out_path}")
    print("WHILE THIS RUNS: every ~20s, write down the elapsed time shown below and")
    print("the temperature(s) on the meter LCD (both channels if it shows two).")
    print("press Ctrl-C to stop early; everything captured so far is kept.\n")

    records = []
    total = 0
    start = time.monotonic()
    last_status = 0.0
    try:
        while (elapsed := time.monotonic() - start) < args.seconds:
            chunk = ser.read(256)
            if chunk:
                records.append({"t": round(elapsed, 3), "hex": chunk.hex()})
                total += len(chunk)
            if elapsed - last_status >= 2:
                last_status = elapsed
                tail = records[-1]["hex"][:48] if records else "-"
                print(f"\r  elapsed {elapsed:6.1f}s   bytes {total:7d}   last: {tail}",
                      end="", flush=True)
    except KeyboardInterrupt:
        print("\nstopped early")
    finally:
        ser.close()

    header = {
        "port": args.port,
        "baud": args.baud,
        "started": datetime.now().isoformat(timespec="seconds"),
        "duration_s": round(time.monotonic() - start, 1),
        "total_bytes": total,
        "note": "records are (t=seconds from start, hex=raw bytes read)",
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(header) + "\n")
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"\n\nsaved {total} bytes in {len(records)} chunks -> {out_path}")
    if total == 0:
        print("WARNING: zero bytes received. is the meter on? right port? Artisan closed?")
    else:
        print("now: send me this file plus your LCD notes (elapsed time -> temp).")
