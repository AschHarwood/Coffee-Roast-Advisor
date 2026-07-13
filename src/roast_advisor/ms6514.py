"""Decoder for the Mastech MS6514 thermocouple meter serial stream.

Frame format (18 bytes, verified against Artisan's decoder and against two
real captures cross-checked with the meter's LCD):

  bytes 0-1   signature 0x65 0x14 ("e" 0x14 — the device id)
  bytes 5-6   main display value,      16-bit big-endian, tenths of a degree
  bytes 7-8   secondary display value, 16-bit big-endian, tenths of a degree
  byte  11    main display status: which channel it shows and whether the
              probe is connected (0x08=T1, 0x09=T2, 0x40-0x43/0xC2-0xC3=NC,
              0x0A/0x8A/0x0B/0x8B = T1-T2 difference modes)
  byte  12    secondary display status: 0x40 = probe not connected
  bytes 16-17 trailer CR LF

The meter streams ~2 frames/second, unprompted. Units are whatever the meter
is set to display (this user: F). A disconnected channel decodes to None.
"""

FRAME_LEN = 18
SIGNATURE = b"\x65\x14"
TRAILER = b"\r\n"

_MAIN_NC = set(range(0x40, 0x44)) | {0xC2, 0xC3}


def decode_frame(frame):
    """One 18-byte frame -> (bean_temp, second_temp), None for a missing probe.

    The meter's main display is the connected probe (status byte says which
    channel); we return it first. Difference modes (T1-T2) are not used in
    this setup and decode to (None, None) so a misconfigured meter fails
    loudly instead of feeding garbage temps.
    """
    if len(frame) != FRAME_LEN or frame[:2] != SIGNATURE or frame[16:] != TRAILER:
        return None, None
    status_main = frame[11]
    status_second = frame[12]
    if status_main not in (0x08, 0x09):
        return None, None
    main = (frame[5] * 256 + frame[6]) / 10
    second = (frame[7] * 256 + frame[8]) / 10 if status_second != 0x40 else None
    return main, second


class FrameStream:
    """Incremental frame extractor: feed raw bytes as they arrive, get frames.

    Handles frames split across reads and garbage between frames (resyncs on
    the signature). Keeps at most one partial frame of state.
    """

    def __init__(self):
        self._buf = b""

    def feed(self, data):
        self._buf += data
        frames = []
        while True:
            i = self._buf.find(SIGNATURE)
            if i < 0:
                # keep a trailing 0x65 in case the signature was split
                self._buf = self._buf[-1:] if self._buf.endswith(b"\x65") else b""
                return frames
            if len(self._buf) - i < FRAME_LEN:
                self._buf = self._buf[i:]
                return frames
            candidate = self._buf[i : i + FRAME_LEN]
            if candidate[16:] == TRAILER:
                frames.append(candidate)
                self._buf = self._buf[i + FRAME_LEN :]
            else:
                # false signature match inside garbage: skip past it
                self._buf = self._buf[i + 2 :]


def read_capture(path):
    """A capture .jsonl (from `uv run capture`) -> list of (t, raw_bytes)."""
    import json

    chunks = []
    with open(path) as f:
        next(f)  # header line
        for line in f:
            r = json.loads(line)
            chunks.append((r["t"], bytes.fromhex(r["hex"])))
    return chunks
