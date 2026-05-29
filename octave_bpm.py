# MIT License
#
# Copyright (c) 2026 OffbeatDev
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# requires: librosa>=0.10, numpy

# uses librosa (https://librosa.org), ISC License
# librosa copyright (c) 2013--2023, librosa development team. ISC License preserved.

"""
octave_bpm.py — beat-aware BPM detection with octave-error correction.

librosa's default tempo estimator works on the tempogram and can return a value
that is exactly half or double (or a nearby harmonic) of the true BPM.  This
module adds a lightweight post-processing step that re-scores candidate octave
multiples against the song's onset-strength envelope via autocorrelation, then
picks the candidate whose implied period best explains the observed rhythmic
energy.

Algorithm (``_resolve_octave``):
  1. Compute the onset-strength envelope with ``librosa.onset.onset_strength``.
  2. Build a tempogram and get an initial BPM estimate via
     ``librosa.beat.tempo``.
  3. Generate six candidate BPMs as octave multiples of the raw estimate:
       0.5×, 0.75×, 1.0×, 1.33×, 1.5×, 2.0×
  4. For each candidate, convert its period to a lag (in frames) in the onset
     envelope, then read the autocorrelation of the onset envelope at that lag.
     Higher autocorrelation means the onset pattern repeats at that period —
     i.e. the candidate BPM is consistent with the actual rhythmic pulse.
  5. Clamp candidates to a musically sane range (55–200 BPM) and return the
     best-scoring one.
  6. Compute ``beat_offset_ms``: the time (in milliseconds) from the start of
     the audio to the first detected beat at the corrected BPM.

This approach was extracted from the DiscoForge detection pipeline.  It works
well on four-on-the-floor and backbeat-heavy music; results on freely-swung or
polyrhythmic material may vary.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import librosa


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

_OCTAVE_FACTORS = (0.5, 0.75, 1.0, 1.33, 1.5, 2.0)
_BPM_MIN = 55.0
_BPM_MAX = 200.0


# ---------------------------------------------------------------------------
# core helpers
# ---------------------------------------------------------------------------

def _onset_autocorr(onset_env: np.ndarray, lag_frames: int) -> float:
    """Return the normalised autocorrelation of *onset_env* at *lag_frames*."""
    if lag_frames <= 0 or lag_frames >= len(onset_env):
        return 0.0
    a = onset_env[:-lag_frames]
    b = onset_env[lag_frames:]
    denom = np.sqrt(np.dot(a, a) * np.dot(b, b))
    if denom < 1e-9:
        return 0.0
    return float(np.dot(a, b) / denom)


def _resolve_octave(
    onset_env: np.ndarray,
    raw_bpm: float,
    hop_length: int,
    sr: int,
) -> float:
    """Score octave-related BPM candidates and return the best one.

    Parameters
    ----------
    onset_env:
        Onset-strength envelope produced by ``librosa.onset.onset_strength``.
    raw_bpm:
        Initial BPM estimate (e.g. from ``librosa.beat.tempo``).
    hop_length:
        Hop length used when computing *onset_env* (frames → seconds conversion).
    sr:
        Audio sample rate.

    Returns
    -------
    float
        The candidate BPM with the highest autocorrelation score, clamped to
        [``_BPM_MIN``, ``_BPM_MAX``].
    """
    hop_s = hop_length / sr  # seconds per onset frame

    best_bpm = raw_bpm
    best_score = -1.0

    for factor in _OCTAVE_FACTORS:
        candidate = raw_bpm * factor
        if candidate < _BPM_MIN or candidate > _BPM_MAX:
            continue
        period_s = 60.0 / candidate
        lag = int(round(period_s / hop_s))
        score = _onset_autocorr(onset_env, lag)
        if score > best_score:
            best_score = score
            best_bpm = candidate

    return best_bpm


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def detect_bpm(path: str | Path, hop_length: int = 512) -> tuple[float, float]:
    """Detect BPM and beat offset for an audio file.

    Parameters
    ----------
    path:
        Path to an audio file.  Any format supported by librosa / soundfile is
        accepted (MP3, WAV, FLAC, OGG, M4A …).
    hop_length:
        STFT hop length.  512 at sr=22050 gives ~23 ms frame resolution;
        changing this trades speed for precision.

    Returns
    -------
    (bpm, beat_offset_ms):
        *bpm* — corrected tempo in beats per minute (float).
        *beat_offset_ms* — time from the audio start to the first beat, in
        milliseconds (float).  Negative values are clamped to 0.
    """
    y, sr = librosa.load(str(path), sr=22050, mono=True)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    raw_bpm_arr = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
    raw_bpm = float(raw_bpm_arr[0])

    bpm = _resolve_octave(onset_env, raw_bpm, hop_length, sr)

    _, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
        bpm=bpm,
        tightness=100.0,
    )

    if len(beat_frames) > 0:
        beat_offset_ms = max(0.0, librosa.frames_to_time(beat_frames[0], sr=sr, hop_length=hop_length) * 1000.0)
    else:
        beat_offset_ms = 0.0

    return round(bpm, 2), round(beat_offset_ms, 1)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python octave_bpm.py path/to/song.mp3", file=sys.stderr)
        sys.exit(1)

    audio_path = sys.argv[1]
    if not Path(audio_path).exists():
        print(f"error: file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    bpm, offset_ms = detect_bpm(audio_path)
    print(f"BPM: {bpm}, Offset: {offset_ms} ms")
