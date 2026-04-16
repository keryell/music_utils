# music_utils

[![Tests](https://github.com/keryell/music_utils/actions/workflows/test.yml/badge.svg)](https://github.com/keryell/music_utils/actions/workflows/test.yml)

Tools for processing [ABC music notation](https://abcnotation.com/wiki/abc:standard:v2.2) files.

These tools are mainly used in the
[Kazimodal](https://github.com/keryell/musique) music project.

## abccat

Concatenates multiple ABC tunes into a single multi-part tune,
collecting `P:` (part order) headers into a global play-order string.

### Header handling

An ABC tune has a **header** (from `X:` to `K:`) and a **body**
(the music after `K:`).  When merging tunes, the first tune's
header becomes the combined header, and everything from subsequent
tunes ends up in the body.  The problem is that abc2midi's parser
only accepts certain header fields in the body (`E I K L M P Q T V
d r s w W +`) and rejects the rest.

So headers are handled to maximize compatibility with both
[abcm2ps](http://moinejf.free.fr/) (visual rendering) and
[abc2midi](https://abc.sourceforge.net/abcMIDI/) (MIDI output):

- `T:` (title) is allowed in the body by abc2midi (emitted as a
  MIDI sequence\_name meta-event), so it is always kept as an active
  header.
- `C:` (composer) and `R:` (rhythm) are valid in the header but
  **rejected in the body**.  They are kept as active headers for the
  first tune (which lands in the combined header) but demoted to
  `%%text` comments for subsequent tunes.
- `X:` (reference number) must appear exactly once, so it is always
  demoted.
- Other per-tune metadata (`A:`, `N:`, `S:`, `Z:`, etc.) is not
  recognized in the body and is always demoted to `%%text` comments.

Demoted headers use the `%%text` directive, which renders visually
in abcm2ps printed output but is invisible to abc2midi.  This is the
best available compromise: the metadata remains readable on the
score even though it cannot be embedded in the MIDI output.

### Character encoding

Input files can mix different character encodings.  The encoding of
each file is resolved in this order:

1. **`--encoding` flag** — if given on the command line, it forces
   the encoding for all input files, overriding everything else.
2. **`%%encoding` directive** — if the file contains a line like
   `%%encoding latin1`, that charset is used.
3. **UTF-8 auto-detection** — the file is decoded as UTF-8.
4. **ISO-8859-15 (Latin-9) fallback** — if UTF-8 decoding fails,
   Latin-9 is assumed.  This covers Western European languages
   including the euro sign (€) and French œ/Œ.

The output is always UTF-8.

### Usage

```
abccat tune1.abc tune2.abc > merged.abc
cat tune1.abc tune2.abc | abccat > merged.abc
abccat --encoding iso-8859-15 old_file.abc > merged.abc
abccat -e latin1 legacy1.abc legacy2.abc > merged.abc
```

## Running the tests

```
pip install pytest
pytest tests/ -v
```
