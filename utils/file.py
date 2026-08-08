from enum import Enum
from pathlib import PurePath


class OS_TYPE(Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"


DEFAULT_NAME = "untitled"
# every filesystem we target stops at 255 bytes per path component
MAX_NAME_BYTES = 255

# NUL and the C0 controls are rejected everywhere; DEL trips some tools too
_CONTROL_CHARS = {chr(i) for i in range(32)} | {chr(127)}

_FORBIDDEN_CHARS = {
    OS_TYPE.LINUX: set("/"),
    # ":" is the classic Mac separator and still confuses Finder
    OS_TYPE.MACOS: set("/:"),
    OS_TYPE.WINDOWS: set('<>:"/\\|?*'),
}

# reserved device names, with or without an extension (CON, con.txt, ...)
_WINDOWS_RESERVED = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def _is_meaningless(name: str, replacement: str) -> str:
    """True when nothing but padding survived sanitizing (".", "__", " ")."""
    stripped = name.strip(" .")
    if replacement:
        stripped = stripped.strip(replacement)
    return not stripped


def _truncate_bytes(name: str, limit: int) -> str:
    """Cut name to at most limit utf-8 bytes without splitting a character."""
    encoded = name.encode("utf-8")
    if len(encoded) <= limit:
        return name
    return encoded[:limit].decode("utf-8", errors="ignore")


def _shorten(name: str, limit: int) -> str:
    """Shorten name to the byte limit, keeping its extension when possible."""
    if len(name.encode("utf-8")) <= limit:
        return name

    suffix = PurePath(name).suffix
    stem = name[: len(name) - len(suffix)] if suffix else name
    # an absurdly long "extension" is not worth preserving
    if len(suffix.encode("utf-8")) >= limit:
        return _truncate_bytes(name, limit)

    room = limit - len(suffix.encode("utf-8"))
    return _truncate_bytes(stem, room).rstrip() + suffix


def name_sanitizer(
    filename: str,
    os: OS_TYPE = OS_TYPE.LINUX,
    *,
    replacement: str = "_",
    fallback: str = DEFAULT_NAME,
    max_bytes: int = MAX_NAME_BYTES,
) -> str:
    """Turn arbitrary text into a filename that is safe on the given OS.

    Forbidden and control characters become `replacement`, so path separators
    cannot survive: "../etc/passwd" sanitizes to ".._etc_passwd" rather than
    escaping its directory. Names that end up empty, or that mean something
    special (".", "..", Windows device names), fall back to `fallback`.

    Only the name is handled — pass one path component, not a path.
    """
    if not isinstance(filename, str):
        raise TypeError("filename must be a str")

    forbidden = _FORBIDDEN_CHARS[os] | _CONTROL_CHARS
    cleaned = "".join(replacement if c in forbidden else c for c in filename)

    # leading/trailing blanks are invisible and easy to get wrong
    cleaned = cleaned.strip()
    if os is OS_TYPE.WINDOWS:
        # windows silently drops trailing dots and spaces
        cleaned = cleaned.rstrip(" .")

    if _is_meaningless(cleaned, replacement):
        return fallback

    if os is OS_TYPE.WINDOWS:
        # the device name is matched before the first dot, so "NUL.tar.gz" counts
        if cleaned.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
            cleaned = f"{replacement}{cleaned}"

    cleaned = _shorten(cleaned, max_bytes)
    # shortening can strip everything meaningful back out again
    return fallback if _is_meaningless(cleaned, replacement) else cleaned
