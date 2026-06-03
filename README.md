# discoforge-bpm-tools

beat-aware bpm detection with octave-error correction. mit-licensed reference implementations from the [discoforge](https://discoforge.netlify.app) audio pipeline.

[![ci](https://github.com/sheluvghostii/discoforge-bpm-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/sheluvghostii/discoforge-bpm-tools/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## what this is

a single-file python implementation of the bpm-detection technique used by [discoforge](https://discoforge.netlify.app) — a tool that automates the painful per-song setup process for [dead as disco](https://store.steampowered.com/app/3404260)'s custom song import system.

librosa's default tempo estimator works on the tempogram and can return a value that is exactly half, double, or a nearby harmonic (e.g. 4/3×) of the true bpm — a common failure mode on music with strong sub-beat energy or syncopated patterns. this module adds a post-processing pass that re-scores six octave-related bpm candidates (0.5×, 0.75×, 1.0×, 1.33×, 1.5×, 2.0× the raw estimate) using onset-envelope autocorrelation, then picks the one whose implied beat period best fits the actual rhythmic energy.

## what this is not

this is the detection core. it does not produce a `meta.json`, does not interact with any game engine, does not include the batch processor, the tempo-section detector, or the windows gui. for the full pipeline that turns audio files into ready-to-import dead-as-disco songs, see [discoforge.netlify.app](https://discoforge.netlify.app).

## algorithm

1. load audio at 22 050 hz mono via librosa
2. compute an onset-strength envelope (`librosa.onset.onset_strength`)
3. get an initial bpm from librosa's tempogram-based estimator (`librosa.beat.tempo`)
4. generate six octave candidates: 0.5×, 0.75×, 1.0×, 1.33×, 1.5×, 2.0× the raw estimate
5. for each candidate, convert its bpm period to a lag in onset frames and read the autocorrelation of the onset envelope at that lag — higher autocorrelation means the onset pattern repeats at that period
6. clamp candidates to a musically sane range (55–200 bpm) and pick the highest-scoring one
7. run `librosa.beat.beat_track` at the corrected bpm to find the first beat time (beat offset in ms)
8. return `(bpm, beat_offset_ms)`

the 4/3 and 3/4 factors specifically catch a class of errors common on tracks with triplet or shuffle feel where the raw estimator locks onto a non-integer multiple of the true tempo.

## install

```bash
pip install librosa numpy soundfile
```

no other dependencies. librosa pulls in audioread for format support (mp3, wav, flac, ogg, m4a, etc).

## usage

**from the command line:**

```bash
python octave_bpm.py path/to/song.mp3
```

**from python:**

```python
from octave_bpm import detect_bpm

bpm, offset_ms = detect_bpm("path/to/song.mp3")
print(f"bpm: {bpm}, first-beat offset: {offset_ms} ms")
```

## tests

```bash
pip install librosa numpy soundfile
python tests/test_octave_correction.py
```

the test generates a synthetic 30-second 122-bpm drum pattern (kick on every beat, snare on 2 & 4, hi-hats on 8ths) and asserts that `detect_bpm()` recovers 122 ± 1 bpm. this is the exact failure mode the octave-correction pass was built to fix — on real material, librosa's raw estimator regularly returns 161 (= 4/3 × 122) or 244 (= 2 × 122) on songs at this tempo with strong sub-beat energy.

no audio files required. runs in ~5 seconds on CI.

## known limitations

- assumes a roughly steady tempo across the song — for tracks with intentional mid-song tempo changes, use the full discoforge pipeline which detects up to 5 tempo sections
- targets the 55–200 bpm range — songs below 55 or above 200 will be clamped
- works best on percussive material — purely melodic / ambient music with no clear beat will fall back to whatever librosa's initial guess was
- the autocorrelation score is computed over the full song, so very long sustained tempo drift (more than ~10%) reduces the signal — discoforge handles this case with a separate section detector

## license

mit license. see [LICENSE](LICENSE) and [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for librosa attribution.

## context

this code, the [r/rhythmgames writeup](https://www.reddit.com/r/rhythmgames/comments/1tooyts/), and [discoforge.netlify.app](https://discoforge.netlify.app) are all from the same project. the closed-source desktop app at discoforge.netlify.app wraps this technique into a one-drag-drop pipeline plus tempo-section detection, batch processing, and direct meta.json writing into the dead-as-disco importedsongs folder. the binary is pay-what-you-want with a $0 minimum.

if you want to read more of the engineering write-up, the r/rhythmgames post covers the in-game `customTempoSections` finding and the beat-offset clamp behaviour discovered along the way.
