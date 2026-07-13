"""Stage 1 decoder tests against real captured meter data.

Ground truth: during the room-temp capture the meter LCD read ~78F (user
confirmed); during the warm capture the empty roaster climbed from ~212F
toward its ~300F preheat plateau.
"""

import glob

import pytest

from roast_advisor.ms6514 import FrameStream, decode_frame, read_capture

ROOM_CAPTURE = "tests/fixtures/ms6514_capture_20260712_212634.jsonl"
WARM_CAPTURE = "tests/fixtures/ms6514_capture_20260712_213654.jsonl"


def decode_capture(path):
    stream = FrameStream()
    temps = []
    for _, chunk in read_capture(path):
        for frame in stream.feed(chunk):
            bean, second = decode_frame(frame)
            if bean is not None:
                temps.append(bean)
    return temps


def test_room_capture_matches_lcd():
    temps = decode_capture(ROOM_CAPTURE)
    assert len(temps) >= 190  # ~2 frames/s for 120s
    assert all(abs(t - 78) <= 1.0 for t in temps), (min(temps), max(temps))


def test_warm_capture_is_a_smooth_climb():
    temps = decode_capture(WARM_CAPTURE)
    assert len(temps) >= 140
    assert temps[0] < 220 and temps[-1] > 300
    # monotonic-ish: a thermocouple in a heating chamber never drops sharply
    drops = [a - b for a, b in zip(temps, temps[1:]) if b < a]
    assert not drops or max(drops) < 2.0
    # and never jumps absurdly between 0.5s samples
    assert max(abs(b - a) for a, b in zip(temps, temps[1:])) < 15


def test_second_channel_not_connected_reads_none():
    stream = FrameStream()
    for _, chunk in read_capture(ROOM_CAPTURE):
        for frame in stream.feed(chunk):
            bean, second = decode_frame(frame)
            assert second is None  # no ET probe on this setup


def test_split_and_garbage_resync():
    # take one real frame, split it awkwardly and wrap it in junk
    stream0 = FrameStream()
    chunks = read_capture(ROOM_CAPTURE)
    frame = stream0.feed(b"".join(c for _, c in chunks[:3]))[0]

    s = FrameStream()
    got = []
    got += s.feed(b"\xff\x65")           # garbage ending in half a signature
    got += s.feed(frame[:7])              # signature + partial frame
    got += s.feed(frame[7:] + b"\x00\x65\x14junk")  # rest + a false signature
    got += s.feed(frame)                  # then a clean frame
    assert frame in got
    assert len(got) == 2                  # both real copies, junk dropped


def test_truncated_frame_rejected():
    assert decode_frame(b"\x65\x14short") == (None, None)


def test_difference_mode_fails_loudly():
    # status byte 0x0A = meter showing T1-T2: refuse rather than feed garbage
    chunks = read_capture(ROOM_CAPTURE)
    frame = bytearray(FrameStream().feed(b"".join(c for _, c in chunks[:3]))[0])
    frame[11] = 0x0A
    assert decode_frame(bytes(frame)) == (None, None)
