"""
Where the extracted game client DB lives.

It is not shipped with the app - it comes from unpacking the game's own data files, so most machines
do not have it. The optimizer's precise damage classifier, the effect indexes and the character
extraction scripts all read it, and each falls back quietly when it is absent.

Set CZN_CLIENT_DB to the extracted output folder, the one containing `db/` and `text/`. Without it, the
folder the Setup page last extracted into is used.
"""

import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Callable

ENV_VAR = "CZN_CLIENT_DB"

# The repo root when running from source. Frozen builds have no repo, so this is only meaningful in dev.
REPO_ROOT = Path(__file__).resolve().parent.parent

# The app's own folder: the install folder when frozen, `api/` from source. Mirrors `BASE_DIR` in api/capture/constants.py,
# which cannot be imported here because the capture package pulls in mitmproxy.
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else REPO_ROOT / "api"

# Settings saved by the Setup page's extraction card, beside the other snapshots-folder settings.
SETTINGS_FILE = APP_DIR / "snapshots" / "game_data_extract.json"

# The original author's path. Kept last so their machine keeps working with no configuration, but it
# means every other machine silently got an empty index before this was configurable.
_LEGACY_OUTPUT = Path(r"C:\Users\soste\Downloads\output")

# Callbacks from modules that cache things derived from the client data, run by `reset_caches()`.
_reset_hooks: list[Callable[[], None]] = []


def load_extract_settings() -> dict:
    """
    The settings saved by the extraction card.

    Returns:
        The saved fields, or an empty dict when the file is missing or unreadable.
    """
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_extract_settings(settings: dict) -> None:
    """
    Replace the settings saved by the extraction card.

    Args:
        settings: The full set of saved fields.
    """
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def client_output_dir() -> Path:
    """
    Root of the extracted client data, holding `db/` and `text/`.

    Returns:
        The path from CZN_CLIENT_DB, else the saved extraction folder if it holds a `db/`, else `default_extract_dir()`
        if it exists, else the legacy one. Not guaranteed to exist - callers check.
    """
    env = os.environ.get(ENV_VAR, "").strip()
    if env:
        return Path(env)
    saved = str(load_extract_settings().get("out_dir") or "").strip()
    if saved and (Path(saved) / "db").is_dir():
        return Path(saved)
    default = default_extract_dir()
    if default.exists():
        return default
    return _LEGACY_OUTPUT


def default_extract_dir() -> Path:
    """
    Where the Setup page extracts to when the user has not picked a folder.

    Returns:
        `client_db/` in the install folder when frozen, else in the repo root.
    """
    return (APP_DIR if getattr(sys, "frozen", False) else REPO_ROOT) / "client_db"


def client_db_dir() -> Path:
    """
    The `db/` folder holding the shard JSONs.

    Returns:
        `<client_output_dir()>/db`. Not guaranteed to exist.
    """
    return client_output_dir() / "db"


def have_client_db() -> bool:
    """
    Whether the client DB is actually present.

    Returns:
        True if the `db/` folder exists, so callers can skip or fall back instead of failing.
    """
    return client_db_dir().is_dir()


def client_text_file() -> Path:
    """
    The English text catalogue, which holds display names.

    Returns:
        `<client_output_dir()>/text/en/text.json`. Not guaranteed to exist.
    """
    return client_output_dir() / "text" / "en" / "text.json"


def have_client_text() -> bool:
    """
    Whether the text catalogue is present.

    Separate from `have_client_db` because an export can stop early and leave the shard JSONs
    without it. Anything that resolves names needs this as well.

    Returns:
        True if the catalogue exists.
    """
    return client_text_file().is_file()


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Reading it


@lru_cache(maxsize=None)
def _load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def table(name: str, root: Path | None = None) -> list[dict]:
    """
    One shard JSON from the client's `db` folder.

    The files run to megabytes and the extraction scripts read the same handful of them once per
    res_id, so the result is cached for the life of the process. Treat what comes back as read only.

    Args:
        name: The file name inside `db`, such as "char_base@char_base.json".
        root: Root of the unpacked client, defaulting to the configured one.

    Returns:
        The rows, in file order.
    """
    base = (root / "db") if root is not None else client_db_dir()
    return json.loads(_load(str(base / name)))


@lru_cache(maxsize=None)
def _index(path: str) -> dict[str, dict]:
    return {str(row["id"]): row for row in json.loads(_load(path)) if "id" in row}


def table_by_id(name: str, root: Path | None = None) -> dict[str, dict]:
    """
    One shard JSON keyed by its `id` column.

    Args:
        name: The file name inside `db`.
        root: Root of the unpacked client, defaulting to the configured one.

    Returns:
        id -> row, cached. Treat it as read only.
    """
    base = (root / "db") if root is not None else client_db_dir()
    return _index(str(base / name))


@lru_cache(maxsize=None)
def _text_index(path: str) -> dict[str, str]:
    return {str(row["id"]): row.get("text") for row in json.loads(_load(path)) if row.get("id")}


def text_index(root: Path | None = None) -> dict[str, str]:
    """
    The English text catalogue as a lookup.

    The file is over 13 MB, and every display name, skill name and description in the client is a key
    in it, so scanning it per lookup is what makes the extraction scripts slow.

    Args:
        root: Root of the unpacked client, defaulting to the configured one.

    Returns:
        text key -> display string, cached. Treat it as read only.
    """
    path = (root / "text" / "en" / "text.json") if root is not None else client_text_file()
    return _text_index(str(path))


def on_reset(hook: Callable[[], None]) -> None:
    """
    Register a callback that drops a cache built from the client data.

    Args:
        hook: Called with no arguments by `reset_caches()`.
    """
    _reset_hooks.append(hook)


def reset_caches() -> None:
    """Drop everything read from the client so the next read picks up a fresh extraction."""
    _load.cache_clear()
    _index.cache_clear()
    _text_index.cache_clear()
    for hook in _reset_hooks:
        hook()
