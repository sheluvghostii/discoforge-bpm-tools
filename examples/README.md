# examples

reference `meta.json` files that match the shape dead as disco expects in its `importedsongs/<song>/meta.json` location. these were used during the engineering writeup posted at [r/rhythmgames](https://www.reddit.com/r/rhythmgames/comments/1tooyts/) to test the four behaviours described there.

| file | shape | what it tests |
|---|---|---|
| `sample_meta_steady_bpm.json` | single tempo, no sections | the baseline case — most pop / disco / phonk tracks |
| `sample_meta_tempo_sections.json` | top-level `tempo` + a few `customTempoSections` | the in-game finding that `customTempoSections` does not actually drive combat timing — only the top-level `tempo` field does |
| `sample_meta_tempo_swings.json` | many wide-swing tempo sections | the failure case that causes the song to silently vanish from the in-game library (more than ~50 entries) |
| `sample_meta_beat_offset.json` | extreme `beatOffset` value | the hard-clamp behaviour at ±250 ms |

these files do not include audio. they document the file format and the engine quirks the discoforge writeup discusses.

## reading the files

```python
import json

with open("examples/sample_meta_steady_bpm.json") as f:
    meta = json.load(f)

print(meta["tempo"], meta.get("beatOffset"), len(meta.get("customTempoSections", [])))
```

## what discoforge does with these

the full [discoforge](https://discoforge.pplx.app) pipeline generates files of this shape automatically from an audio file, picking the right tempo, beat offset, and section count for the song. this repo only contains the bpm-detection step — the file generation, section detection, and import-folder writing live in the closed-source desktop app.
