# contributing

small repo, simple rules.

## what kind of contributions are welcome

- bug reports on edge cases where octave correction picks the wrong candidate
- additional test cases with synthetic or freely-licensed audio
- algorithm improvements that keep the single-file structure intact
- doc fixes, clarifications, typos

## what's out of scope

- adding new pipeline stages (`meta.json` generation, tempo sections, batch processing, gui) — those live in the closed-source [discoforge](https://discoforge.pplx.app) app, not here. this repo is intentionally a single technique extracted as a reference
- copyrighted audio in tests or examples — only synthetic or freely-licensed material

## development

```bash
git clone https://github.com/sheluvghostii/discoforge-bpm-tools.git
cd discoforge-bpm-tools
pip install librosa>=0.10 numpy soundfile
python tests/test_octave_correction.py
```

## style

- no formatting tool required — just match the existing style (lowercase comments, type hints, short functions, numpy-style docstrings)
- prefer adding a synthetic test over describing a regression in prose
- keep the public api stable: `detect_bpm(path) -> (bpm, offset_ms)`

## license

contributions are accepted under the mit license of the project (see [LICENSE](LICENSE)).
