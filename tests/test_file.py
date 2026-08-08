import pytest

from utils.file import DEFAULT_NAME, MAX_NAME_BYTES, OS_TYPE, name_sanitizer

ALL_OS = list(OS_TYPE)


@pytest.mark.parametrize("os_type", ALL_OS)
def test_ordinary_names_are_untouched(os_type):
    assert name_sanitizer("movie.mkv", os_type) == "movie.mkv"
    assert name_sanitizer("a name with spaces.txt", os_type) == "a name with spaces.txt"
    assert name_sanitizer("한글 파일.txt", os_type) == "한글 파일.txt"


def test_defaults_to_linux():
    # ":" is legal on linux but not on windows or macos
    assert name_sanitizer("a:b.txt") == "a:b.txt"


@pytest.mark.parametrize("os_type", ALL_OS)
def test_path_separators_cannot_survive(os_type):
    assert "/" not in name_sanitizer("a/b/c.txt", os_type)
    assert name_sanitizer("../../etc/passwd", os_type) == ".._.._etc_passwd"


@pytest.mark.parametrize("os_type", ALL_OS)
def test_control_characters_are_replaced(os_type):
    assert name_sanitizer("a\x00b\nc.txt", os_type) == "a_b_c.txt"
    assert name_sanitizer("tab\there", os_type) == "tab_here"


def test_windows_forbidden_characters():
    assert name_sanitizer('a<b>c:d"e|f?g*h.txt', OS_TYPE.WINDOWS) == "a_b_c_d_e_f_g_h.txt"
    assert name_sanitizer("back\\slash.txt", OS_TYPE.WINDOWS) == "back_slash.txt"


def test_macos_colon_is_replaced():
    assert name_sanitizer("10:30 meeting.txt", OS_TYPE.MACOS) == "10_30 meeting.txt"
    # but a backslash is a legal macos filename character
    assert name_sanitizer("back\\slash.txt", OS_TYPE.MACOS) == "back\\slash.txt"


@pytest.mark.parametrize("os_type", ALL_OS)
@pytest.mark.parametrize("name", ["", "   ", ".", "..", "/", "\x00"])
def test_meaningless_names_fall_back(os_type, name):
    assert name_sanitizer(name, os_type) == DEFAULT_NAME


@pytest.mark.parametrize("name", ["CON", "con", "NUL.txt", "com1", "LPT9.tar.gz", "AuX"])
def test_windows_reserved_names_are_escaped(name):
    sanitized = name_sanitizer(name, OS_TYPE.WINDOWS)

    assert sanitized == f"_{name}"
    # the same names are fine elsewhere
    assert name_sanitizer(name, OS_TYPE.LINUX) == name


def test_windows_reserved_word_inside_a_name_is_kept():
    assert name_sanitizer("console.log", OS_TYPE.WINDOWS) == "console.log"
    assert name_sanitizer("my CON file.txt", OS_TYPE.WINDOWS) == "my CON file.txt"


def test_windows_drops_trailing_dots_and_spaces():
    assert name_sanitizer("report.txt.  ", OS_TYPE.WINDOWS) == "report.txt"
    assert name_sanitizer("name...", OS_TYPE.WINDOWS) == "name"
    # linux keeps them
    assert name_sanitizer("name...", OS_TYPE.LINUX) == "name..."


@pytest.mark.parametrize("os_type", ALL_OS)
def test_surrounding_whitespace_is_stripped(os_type):
    assert name_sanitizer("  spaced.txt  ", os_type) == "spaced.txt"


@pytest.mark.parametrize("os_type", ALL_OS)
def test_long_names_are_truncated_keeping_the_extension(os_type):
    name = "a" * 400 + ".mkv"

    sanitized = name_sanitizer(name, os_type)

    assert len(sanitized.encode()) <= MAX_NAME_BYTES
    assert sanitized.endswith(".mkv")


@pytest.mark.parametrize("os_type", ALL_OS)
def test_truncation_never_splits_a_character(os_type):
    name = "한" * 200 + ".txt"

    sanitized = name_sanitizer(name, os_type)

    assert len(sanitized.encode()) <= MAX_NAME_BYTES
    assert sanitized.endswith(".txt")
    sanitized.encode().decode()  # would raise if a character were cut in half


def test_absurd_extension_is_truncated_too():
    sanitized = name_sanitizer("x." + "y" * 400)

    assert len(sanitized.encode()) <= MAX_NAME_BYTES


def test_custom_replacement_and_fallback():
    assert name_sanitizer("a/b", replacement="-") == "a-b"
    assert name_sanitizer("", fallback="download") == "download"


def test_custom_max_bytes():
    assert name_sanitizer("abcdefghij.txt", max_bytes=10) == "abcdef.txt"


def test_non_string_input_is_rejected():
    with pytest.raises(TypeError):
        name_sanitizer(None)
