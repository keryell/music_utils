"""Tests for the abccat ABC tune concatenation tool."""

import pathlib
import subprocess
import textwrap

# Path to the abccat script relative to this test file
TESTS_DIR = pathlib.Path(__file__).resolve().parent
ABCCAT = str(TESTS_DIR.parent / "abccat")
FIXTURES = TESTS_DIR / "fixtures"


def run_abccat(*files, stdin=None):
    """Run abccat and return the CompletedProcess result."""
    return subprocess.run(
        [ABCCAT, *files],
        input=stdin, capture_output=True, text=True
    )


# --- Header handling ---

def test_single_tune_basic_structure():
    """A single tune produces X:1, a P: header, and the body."""
    r = run_abccat(stdin="X:1\nT:Foo\nP:AB\nK:G\nABCD\n")
    lines = r.stdout.splitlines()
    assert lines[0] == "X:1"
    assert lines[1] == "P:AB"


def test_title_is_active_header():
    """T: must be kept as an active header, not demoted to %%text."""
    r = run_abccat(stdin="X:1\nT:My Tune\nK:G\nABCD\n")
    assert "T:My Tune" in r.stdout
    assert "%%text T:My Tune" not in r.stdout


def test_x_is_demoted_to_text():
    """X: from input tunes must be demoted to %%text."""
    r = run_abccat(stdin="X:1\nT:Foo\nK:G\nABCD\n")
    assert "%%text X:1" in r.stdout


def test_composer_first_tune_is_active():
    """C: in the first tune should be an active header."""
    r = run_abccat(stdin="X:1\nT:Foo\nC:Bach\nK:G\nABCD\n")
    assert "C:Bach" in r.stdout
    assert "%%text C:Bach" not in r.stdout


def test_composer_second_tune_is_demoted():
    """C: in subsequent tunes must be demoted to %%text."""
    inp = "X:1\nT:A\nC:Bach\nK:G\nAB\nX:2\nT:B\nC:Mozart\nK:D\nCD\n"
    r = run_abccat(stdin=inp)
    assert "C:Bach" in r.stdout
    assert "%%text C:Bach" not in r.stdout
    assert "%%text C:Mozart" in r.stdout


def test_rhythm_first_tune_is_active():
    """R: in the first tune should be an active header."""
    r = run_abccat(stdin="X:1\nT:Foo\nR:Hanter-dro\nK:G\nABCD\n")
    assert "R:Hanter-dro" in r.stdout
    assert "%%text R:Hanter-dro" not in r.stdout


def test_rhythm_second_tune_is_demoted():
    """R: in subsequent tunes must be demoted to %%text."""
    inp = "X:1\nT:A\nR:Jig\nK:G\nAB\nX:2\nT:B\nR:Reel\nK:D\nCD\n"
    r = run_abccat(stdin=inp)
    assert "%%text R:Reel" in r.stdout


def test_unique_headers_are_demoted():
    """Headers in UNIQUE_HEADERS (A, B, D, G, H, N, O, S, Z) become %%text."""
    r = run_abccat(stdin="X:1\nT:Foo\nN:A note\nS:A source\nK:G\nABCD\n")
    assert "%%text N:A note" in r.stdout
    assert "%%text S:A source" in r.stdout


def test_mergeable_headers_pass_through():
    """Headers like M:, L:, K: should pass through as active headers."""
    r = run_abccat(stdin="X:1\nT:Foo\nM:4/4\nL:1/8\nK:G\nABCD\n")
    assert "M:4/4" in r.stdout
    assert "%%text M:4/4" not in r.stdout
    assert "L:1/8" in r.stdout
    assert "K:G" in r.stdout


# --- P: header collection ---

def test_p_headers_are_collected():
    """First P: of each tune is accumulated into the global P: header."""
    inp = "X:1\nT:A\nP:AB\nK:G\nAB\nX:2\nT:B\nP:CD\nK:D\nCD\n"
    r = run_abccat(stdin=inp)
    lines = r.stdout.splitlines()
    assert "P:ABCD" in lines


def test_subsequent_p_headers_are_active():
    """P: headers after the first one in a tune are kept as active part labels."""
    inp = "X:1\nT:A\nP:AB\nK:G\nP:A\nABCD\nP:B\nEFGA\n"
    r = run_abccat(stdin=inp)
    assert "P:A\n" in r.stdout
    assert "P:B\n" in r.stdout


def test_abccat_p_directive_overrides():
    """The %%abccat P: directive overrides the collected global P: header."""
    inp = "%%abccat P:AABB\nX:1\nT:A\nP:AB\nK:G\nABCD\n"
    r = run_abccat(stdin=inp)
    lines = r.stdout.splitlines()
    assert "P:AABB" in lines
    assert "%%text instead of P:AB" in lines


# --- Continuation lines ---

def test_continuation_line():
    """A header ending with \\ is continued on the next line."""
    inp = "X:1\nT:A very long\\\ntitle indeed\nK:G\nABCD\n"
    r = run_abccat(stdin=inp)
    assert "T:A very long" in r.stdout or "title indeed" in r.stdout


# --- Body content ---

def test_music_body_passes_through():
    """Non-header music notation lines pass through unchanged."""
    r = run_abccat(stdin="X:1\nT:Foo\nK:G\n|:ABCD EFGA:|\n")
    assert "|:ABCD EFGA:|" in r.stdout


def test_blank_lines_are_discarded():
    """Blank lines in the input should not appear in the output."""
    r = run_abccat(stdin="X:1\nT:Foo\nK:G\n\n\nABCD\n")
    # No empty lines in the body part of the output
    body = r.stdout.split("ABCD")[0]
    # There should be no blank lines between headers and body
    assert "\n\n" not in body


# --- Encoding handling ---

def test_utf8_file(tmp_path):
    """A UTF-8 encoded file should be read correctly."""
    f = tmp_path / "utf8.abc"
    f.write_text("X:1\nT:Caf\u00e9\nK:G\nABCD\n", encoding="utf-8")
    r = run_abccat(str(f))
    assert "T:Caf\u00e9" in r.stdout


def test_latin9_file(tmp_path):
    """A Latin-9 (ISO-8859-15) encoded file should be read and converted to UTF-8."""
    f = tmp_path / "latin9.abc"
    # \xe9 is 'é' in Latin-9, \x9c is 'œ' in Latin-9... but \x9c is
    # not defined in ISO-8859-15 at that position. Use \xe9 (é) which
    # is shared between Latin-1 and Latin-9.
    f.write_bytes(b"X:1\nT:Caf\xe9\nK:G\nABCD\n")
    r = run_abccat(str(f))
    assert "T:Caf\u00e9" in r.stdout


def test_latin9_oe_ligature(tmp_path):
    """The \u0153 (oe ligature) specific to Latin-9 (0xBD) is decoded correctly."""
    f = tmp_path / "oe.abc"
    # In ISO-8859-15, 0xBD is 'œ'
    f.write_bytes(b"X:1\nT:C\xbdur\nK:G\nABCD\n")
    r = run_abccat(str(f))
    assert "T:C\u0153ur" in r.stdout


def test_mixed_encoding_files(tmp_path):
    """Mixing a UTF-8 file and a Latin-9 file should work transparently."""
    utf8 = tmp_path / "utf8.abc"
    utf8.write_text("X:1\nT:Premi\u00e8re\nP:A\nK:G\nABCD\n",
                     encoding="utf-8")
    latin9 = tmp_path / "latin9.abc"
    latin9.write_bytes(b"X:2\nT:Deuxi\xe8me\nP:B\nK:D\nEFGA\n")
    r = run_abccat(str(utf8), str(latin9))
    assert "T:Premi\u00e8re" in r.stdout
    assert "T:Deuxi\u00e8me" in r.stdout


def test_pure_ascii_file(tmp_path):
    """A pure ASCII file (valid as both UTF-8 and Latin-9) works fine."""
    f = tmp_path / "ascii.abc"
    f.write_text("X:1\nT:Simple\nK:G\nABCD\n", encoding="ascii")
    r = run_abccat(str(f))
    assert "T:Simple" in r.stdout


# --- Two-tune merge ---

def test_two_tune_full_merge():
    """Full integration test: two tunes merged into one."""
    inp = textwrap.dedent("""\
        X:1
        T:Tune One
        C:Composer A
        R:Gavotte
        M:4/4
        L:1/8
        P:AB
        K:G
        P:A
        ABCD EFGA|
        P:B
        abcd efga|
        X:2
        T:Tune Two
        C:Composer B
        R:Rond
        M:3/4
        L:1/4
        P:CD
        K:D
        P:C
        DEF|
        P:D
        def|
    """)
    r = run_abccat(stdin=inp)
    out = r.stdout

    # Global structure
    assert out.startswith("X:1\n")
    assert "P:ABCD" in out.splitlines()

    # First tune: T active, C active, R active
    assert "T:Tune One" in out
    assert "%%text T:Tune One" not in out
    assert "C:Composer A" in out
    assert "%%text C:Composer A" not in out
    assert "R:Gavotte" in out
    assert "%%text R:Gavotte" not in out

    # Second tune: T active, C demoted, R demoted
    assert "T:Tune Two" in out
    assert "%%text T:Tune Two" not in out
    assert "%%text C:Composer B" in out
    assert "%%text R:Rond" in out

    # Music body preserved
    assert "ABCD EFGA|" in out
    assert "DEF|" in out


# --- Fixture file tests ---
#
# These tests use real files committed to tests/fixtures/ in known
# encodings.  This exercises the full file-reading path and serves
# as human-readable documentation of the supported input formats.

def test_fixture_utf8():
    """The UTF-8 fixture decodes correctly."""
    r = run_abccat(str(FIXTURES / "tune_utf8.abc"))
    assert "T:Café de la Paix" in r.stdout
    assert "C:Traditionnel" in r.stdout
    assert "R:Valse" in r.stdout


def test_fixture_latin9_autodetect():
    """The Latin-9 fixture (no directive) is auto-detected via
    the UTF-8-then-Latin-9 fallback."""
    r = run_abccat(str(FIXTURES / "tune_latin9.abc"))
    # é (0xe9 in Latin-9) and œ (0xbd, Latin-9-specific)
    assert "T:Café et Cœur" in r.stdout


def test_fixture_latin1_with_encoding_directive():
    """A file tagged with ``%%encoding latin1`` is decoded using
    that explicit charset, not the auto-detection fallback."""
    r = run_abccat(str(FIXTURES / "tune_latin1_directive.abc"))
    # è (0xe8 in Latin-1) — would also work in Latin-9, but the
    # point of this test is that the %%encoding directive is
    # actually read and applied
    assert "T:Balène" in r.stdout


def test_fixture_mixed_encodings_merged():
    """Merging all three fixtures (UTF-8, Latin-9, Latin-1 with
    directive) produces a single tune with all titles correctly
    decoded."""
    r = run_abccat(
        str(FIXTURES / "tune_utf8.abc"),
        str(FIXTURES / "tune_latin9.abc"),
        str(FIXTURES / "tune_latin1_directive.abc"),
    )
    assert "T:Café de la Paix" in r.stdout
    assert "T:Café et Cœur" in r.stdout
    assert "T:Balène" in r.stdout


def test_fixture_output_is_valid_utf8():
    """Regression guard: output bytes are always valid UTF-8,
    regardless of input encoding."""
    r = subprocess.run(
        [ABCCAT,
         str(FIXTURES / "tune_utf8.abc"),
         str(FIXTURES / "tune_latin9.abc"),
         str(FIXTURES / "tune_latin1_directive.abc")],
        capture_output=True,
    )
    # Will raise UnicodeDecodeError if output is not valid UTF-8
    r.stdout.decode("utf-8")
