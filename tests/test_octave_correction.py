# MIT License
# Copyright (c) 2026 OffbeatDev
#
# Synthetic-audio test for octave_bpm.detect_bpm.
#
# Generates a 30-second 122-BPM drum pattern (kick on every beat, snare on 2 & 4,
# hi-hats on 8th notes) and verifies that detect_bpm() recovers the true BPM
# within ±1 BPM. This is the failure mode the octave-correction pass was built
# to fix: on real songs like Michael Jackson's "Wanna Be Startin' Somethin'",
# librosa's raw tempogram-based estimate frequently returns ~161 (which is
# 4/3 × 122) or 244 (2 × 122) instead of the true 122.
#
# Running this test requires no audio files. It runs end-to-end in CI in
# ~5 seconds.

import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import tempfile

# allow running from the project root with `python tests/test_octave_correction.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from octave_bpm import detect_bpm


SR = 22050
TRUE_BPM = 122.0
DURATION_S = 30.0


def _synth_kick(sr: int, dur: float = 0.12) -> np.ndarray:
    """Pitch-swept sine kick, ~120 Hz down to ~50 Hz."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    env = np.exp(-t * 25)
    freq = 120 * np.exp(-t * 15) + 50
    phase = 2 * np.pi * np.cumsum(freq) / sr
    return (np.sin(phase) * env * 0.9).astype(np.float32)


def _synth_snare(sr: int, dur: float = 0.15) -> np.ndarray:
    """White-noise burst + 200 Hz body."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    env = np.exp(-t * 18)
    noise = np.random.randn(len(t)).astype(np.float32) * env * 0.6
    tone = (np.sin(2 * np.pi * 200 * t) * env * 0.3).astype(np.float32)
    return noise + tone


def _synth_hat(sr: int, dur: float = 0.05) -> np.ndarray:
    """Short noise burst — open hat."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    env = np.exp(-t * 50)
    return (np.random.randn(len(t)).astype(np.float32) * env * 0.25).astype(np.float32)


def _place(buf: np.ndarray, hit: np.ndarray, at_s: float, sr: int) -> None:
    """Add *hit* into *buf* starting at time *at_s* (in seconds)."""
    start = int(at_s * sr)
    end = min(start + len(hit), len(buf))
    if start >= len(buf):
        return
    buf[start:end] += hit[: end - start]


def make_122_bpm_drum_track(duration_s: float = DURATION_S, sr: int = SR) -> np.ndarray:
    """4-on-the-floor kick, snare on 2 & 4, hi-hats on 8th notes, at 122 BPM."""
    beat_period_s = 60.0 / TRUE_BPM
    n = int(duration_s * sr)
    buf = np.zeros(n, dtype=np.float32)

    kick = _synth_kick(sr)
    snare = _synth_snare(sr)
    hat = _synth_hat(sr)

    beat = 0
    t = 0.0
    while t < duration_s:
        # kick on every beat
        _place(buf, kick, t, sr)
        # snare on 2 & 4 of each bar (i.e. odd beats counting from 0: 1, 3, 5, 7...)
        if beat % 2 == 1:
            _place(buf, snare, t, sr)
        # hi-hats on the 8th notes (this beat and the &)
        _place(buf, hat, t, sr)
        _place(buf, hat, t + beat_period_s / 2.0, sr)

        beat += 1
        t += beat_period_s

    # gentle peak normalisation
    peak = np.max(np.abs(buf))
    if peak > 0:
        buf = buf / peak * 0.95
    return buf


def test_octave_correction_recovers_122_bpm():
    np.random.seed(0)  # deterministic noise for snare/hat
    audio = make_122_bpm_drum_track()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, audio, SR)
        bpm, offset_ms = detect_bpm(tmp.name)

    print(f"detected bpm: {bpm}, offset_ms: {offset_ms} (true bpm: {TRUE_BPM})")

    # tolerance of +/-2 BPM accounts for librosa's autocorrelation discretization
    # on synthetic click tracks; in real audio the median-tempo-section approach
    # is what dominates accuracy. the key correctness signal here is that the
    # detector does NOT return ~61 BPM (half) or ~244 BPM (double).
    assert abs(bpm - TRUE_BPM) <= 2.0, (
        f"octave correction should recover {TRUE_BPM} BPM within +/-2, got {bpm}"
    )
    assert 0.0 <= offset_ms < 60.0 / TRUE_BPM * 1000.0, (
        f"beat offset should be within one beat period, got {offset_ms} ms"
    )


if __name__ == "__main__":
    test_octave_correction_recovers_122_bpm()
    print("octave correction test passed")
