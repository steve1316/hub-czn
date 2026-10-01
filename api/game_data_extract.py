"""
Pulls the client data the app reads out of the installed game.

Runs the headless `ChaosZeroNightmareRipper-CLI.exe` from Chaos-Zero-Nightmare-ASSet-Ripper against the game's archive and extracts only
the folders the repo reads. In dev mode it can then run `scripts/add_character.py` against the result to write any new combatants
and partners into the source tree. One job runs at a time, and the Setup page polls its state.
"""

from __future__ import annotations

import codecs
import os
import re
import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from api import client_db

# The archive folders that feed the app and the extraction scripts. See docs/adding-a-character.md.
FOLDERS = ("db", "face/character", "text/en", "tp_skill")

# STOVE registers the game under this uninstall key. Its `DisplayIcon` points at the loader inside `bin`.
UNINSTALL_KEYS = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Stove App STOVE_CHAOSZERO",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Stove App STOVE_CHAOSZERO",
)

# Where the game's archive sits relative to its `bin` folder, newest layout first. A late September 2026 update replaced the
# single `data.pack` with `gameres/manifest.ssra` plus chunk files. The CLI reads either.
PACKS_UNDER_BIN = (Path("appdata") / "cznlive" / "gameres" / "manifest.ssra", Path("appdata") / "cznlive" / "data.pack")

# The stock install's `bin` folder, tried when the registry has nothing usable.
DEFAULT_BIN = Path(r"C:\Program Files (x86)\Games\ChaosZeroNightmare\bin")

ADD_CHARACTER_SCRIPT = client_db.REPO_ROOT / "scripts" / "add_character.py"

# How many log lines a job keeps.
LOG_LIMIT = 500

# The CLI's exit codes, per its --help.
EXIT_MESSAGES = {
    0: "Extracted all four folders.",
    1: "The CLI rejected the arguments (usage error).",
    2: "Could not open or scan the pack. Check the game path, and that the game is not mid-update.",
    3: "Some folders were missing or failed. See czn_ripper.log in the output folder.",
    4: "None of the folders could be extracted.",
}

_BREAK_RE = re.compile(r"\r\n|\r|\n")

# The CLI prints its progress as whole lines when piped instead of redrawing with a carriage return. These go to the progress line.
_PROGRESS_LINE_RE = re.compile(r"^\s*(Scanning|Extracting) \d+%")


@dataclass
class Job:
    """One extraction or add_character.py run, as the Setup page sees it."""

    # "extract", "dry_run" or "apply". An extraction that chains into the dev dry run switches to "dry_run" for that step.
    kind: str
    # "running", "ok", "failed" or "cancelled".
    state: str = "running"
    # Finished output lines, the last `LOG_LIMIT` of them.
    log: deque = field(default_factory=lambda: deque(maxlen=LOG_LIMIT))
    # The latest progress line, such as the CLI's percentage. Cleared when a step ends.
    progress: str = ""
    # Exit code of the last process that ran, None until one finishes.
    exit_code: int | None = None
    # Plain-language outcome, set when the job ends.
    message: str = ""

    def to_dict(self) -> dict:
        """
        A JSON-ready copy for the status route.

        Returns:
            The fields, with the log as a list.
        """
        return {**vars(self), "log": list(self.log)}


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Locating things


def is_frozen() -> bool:
    """
    Whether this is the PyInstaller build rather than a source checkout.

    Returns:
        True when frozen.
    """
    return bool(getattr(sys, "frozen", False))


def is_dev_mode() -> bool:
    """
    Whether the apply step is available, which needs a source tree to write into.

    Returns:
        True when running from source with `scripts/add_character.py` present.
    """
    return not is_frozen() and ADD_CHARACTER_SCRIPT.is_file()



def bin_from_display_icon(icon: str) -> Path | None:
    """
    Turn the uninstall key's `DisplayIcon` into the game's `bin` folder.

    Args:
        icon: The raw value, such as `C:\\Games\\ChaosZeroNightmare\\bin\\loader.exe,0`.

    Returns:
        The folder holding the loader, or None when the value is empty. Not checked for existence.
    """
    icon = re.sub(r",\s*-?\d+$", "", (icon or "").strip()).strip().strip('"')
    if not icon:
        return None
    return Path(icon).parent


def _read_display_icon() -> str | None:
    """
    Read the game's `DisplayIcon` from the registry.

    Returns:
        The value, or None when the key is missing or this is not Windows.
    """
    try:
        import winreg
    except ImportError:
        return None
    for key_path in UNINSTALL_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "DisplayIcon")
                return str(value)
        except OSError:
            continue
    return None


def detect_pack_path() -> Path | None:
    """
    Find the installed game's archive.

    Returns:
        The first archive in `PACKS_UNDER_BIN` that exists under the `bin` folder from the STOVE uninstall key, else under the
        stock install. None if there is none.
    """
    for bin_dir in (bin_from_display_icon(_read_display_icon() or ""), DEFAULT_BIN):
        if bin_dir is None:
            continue
        for rel in PACKS_UNDER_BIN:
            if (bin_dir / rel).is_file():
                return bin_dir / rel
    return None


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Settings


def load_settings(detected: Path | None = None) -> dict:
    """
    The three paths the card edits, with defaults filled in.

    Args:
        detected: The result of `detect_pack_path()` when the caller already has it, to skip a second registry read.

    Returns:
        `cli_path`, `pack_path` and `out_dir` as strings. `cli_path` is empty until the user picks one. A saved `pack_path` that
        no longer exists is replaced by detection, since game updates move the archive, and is empty if nothing is found.
    """
    saved = client_db.load_extract_settings()
    saved_pack = saved.get("pack_path")
    if saved_pack and not Path(saved_pack).is_file():
        saved_pack = None
    pack = saved_pack or detected or detect_pack_path() or ""
    return {
        "cli_path": str(saved.get("cli_path") or ""),
        "pack_path": str(pack),
        "out_dir": str(saved.get("out_dir") or client_db.default_extract_dir()),
    }


def save_settings(updates: dict) -> dict:
    """
    Merge path changes into the saved settings.

    Args:
        updates: Any of `cli_path`, `pack_path`, `out_dir`. Keys with a None value are left alone.

    Returns:
        The settings after the merge, with defaults filled in.
    """
    saved = client_db.load_extract_settings()
    for key in ("cli_path", "pack_path", "out_dir"):
        value = updates.get(key)
        if value is not None:
            saved[key] = str(value).strip()
    client_db.save_extract_settings(saved)
    return load_settings()


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Output handling


class StreamSplitter:
    """Splits process output into finished log lines and progress updates."""

    def __init__(self):
        self._buf = ""

    def feed(self, text: str) -> list[tuple[str, str]]:
        """
        Add a chunk of output.

        Args:
            text: The decoded chunk.

        Returns:
            `("progress", text)` for each segment ended by a lone carriage return or that looks like a CLI progress line, and
            `("line", text)` for every other segment ended by a newline. Blank progress segments are dropped.
        """
        self._buf += text
        out = []
        while True:
            m = _BREAK_RE.search(self._buf)
            # A trailing \r may be the first half of \r\n, so wait for the next chunk.
            if m is None or (m.group() == "\r" and m.end() == len(self._buf)):
                break
            segment, self._buf = self._buf[:m.start()], self._buf[m.end():]
            if m.group() == "\r" or _PROGRESS_LINE_RE.match(segment):
                if segment.strip():
                    out.append(("progress", segment))
            else:
                out.append(("line", segment))
        return out

    def flush(self) -> list[tuple[str, str]]:
        """
        Return whatever is left once the stream has closed.

        Returns:
            The remainder as one line, or nothing if it was blank.
        """
        rest, self._buf = self._buf.rstrip("\r"), ""
        return [("line", rest)] if rest.strip() else []


def exit_message(code: int) -> str:
    """
    Plain-language meaning of a CLI exit code.

    Args:
        code: The process exit code.

    Returns:
        The message for a known code, else a generic one naming it.
    """
    return EXIT_MESSAGES.get(code, f"The CLI exited with code {code}.")


def missing_output(out_dir: Path) -> list[str]:
    """
    What an extraction should have produced but did not.

    Args:
        out_dir: The extraction folder.

    Returns:
        Relative paths that are missing, empty when the output is usable.
    """
    missing = []
    if not (out_dir / "db").is_dir():
        missing.append("db/")
    if not (out_dir / "text" / "en" / "text.json").is_file():
        missing.append("text/en/text.json")
    return missing


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# The job


class ExtractRunner:
    """Owns the single running job and the process behind it."""

    def __init__(self):
        self._lock = threading.Lock()
        self._job: Job | None = None
        self._proc: subprocess.Popen | None = None
        self._cancelled = False

    def snapshot(self) -> dict | None:
        """
        A copy of the current job for the status route.

        Returns:
            The job's fields, or None when nothing has run since startup.
        """
        with self._lock:
            return self._job.to_dict() if self._job is not None else None

    def is_running(self) -> bool:
        """
        Whether a job is in progress.

        Returns:
            True while running.
        """
        with self._lock:
            return self._job is not None and self._job.state == "running"

    def start_extract(self) -> None:
        """
        Start extracting the four folders, chaining a dry-run apply in dev mode.

        Raises:
            RuntimeError: A job is already running.
            ValueError: A path is missing or does not exist.
        """
        settings = load_settings()
        cli, pack, out = settings["cli_path"], settings["pack_path"], settings["out_dir"]
        if not cli or not Path(cli).is_file():
            raise ValueError("Pick ChaosZeroNightmareRipper-CLI.exe first.")
        if not pack or not Path(pack).is_file():
            raise ValueError("Could not find the game's archive. Pick manifest.ssra from bin\\appdata\\cznlive\\gameres, or data.pack on older installs.")
        if not out:
            raise ValueError("Pick an output folder.")
        cmd = [cli, "--pack", pack, "--out", out]
        for folder in FOLDERS:
            cmd += ["--folder", folder]
        self._begin(Job(kind="extract"), lambda: self._run_extract(cmd, Path(out)))

    def start_apply(self, dry_run: bool) -> None:
        """
        Run `add_character.py` against the output folder.

        Args:
            dry_run: Pass `--dry-run` so nothing is written.

        Raises:
            RuntimeError: A job is already running.
            ValueError: The output folder has no extraction in it.
        """
        out = Path(load_settings()["out_dir"])
        if missing_output(out):
            raise ValueError("The output folder has no extraction yet. Run Extract first.")
        self._begin(Job(kind="dry_run" if dry_run else "apply"), lambda: self._run_apply(out, dry_run))

    def cancel(self) -> bool:
        """
        Stop the running process.

        Returns:
            True if there was one to stop.
        """
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                return False
            self._cancelled = True
            self._proc.terminate()
            return True

    def _begin(self, job: Job, work) -> None:
        with self._lock:
            if self._job is not None and self._job.state == "running":
                raise RuntimeError("An extraction is already running.")
            self._job = job
            self._cancelled = False
        threading.Thread(target=self._guarded, args=(work,), daemon=True, name="game-data-extract").start()

    def _guarded(self, work) -> None:
        try:
            work()
        except Exception as exc:
            self._finish("failed", f"{type(exc).__name__}: {exc}")

    def _run_extract(self, cmd: list[str], out: Path) -> None:
        out.mkdir(parents=True, exist_ok=True)
        code = self._run_process(cmd, cwd=out)
        if code is None:
            return
        if code != 0:
            self._finish("failed", exit_message(code))
            return
        missing = missing_output(out)
        if missing:
            self._finish("failed", f"The CLI finished but {', '.join(missing)} is missing from the output folder.")
            return
        client_db.reset_caches()
        if not is_dev_mode():
            self._finish("ok", f"{exit_message(0)} The app now reads game data from {out}.")
            return
        self._append("Extraction complete. Checking for new combatants and partners...")
        with self._lock:
            self._job.kind = "dry_run"
        self._run_apply(out, dry_run=True)

    def _run_apply(self, out: Path, dry_run: bool) -> None:
        cmd = [sys.executable, "-u", str(ADD_CHARACTER_SCRIPT), str(out)] + (["--dry-run"] if dry_run else [])
        code = self._run_process(cmd, cwd=client_db.REPO_ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if code is None:
            return
        if code != 0:
            self._finish("failed", f"add_character.py exited with code {code}.")
        elif dry_run:
            self._finish("ok", "Dry run finished. Review the log, then Apply to write any new entries.")
        else:
            self._finish("ok", "New entries written to the source tree. Review the diff and restart the sidecar to load them.")

    def _run_process(self, cmd: list[str], cwd: Path, env: dict | None = None) -> int | None:
        """
        Run one process to completion, streaming its output into the job.

        Args:
            cmd: The argv.
            cwd: Working directory.
            env: Environment, defaulting to the sidecar's own.

        Returns:
            The exit code, or None if the job was cancelled or could not start (the job is already finished then).
        """
        self._append(f"> {subprocess.list2cmdline(cmd)}")
        try:
            proc = subprocess.Popen(
                cmd, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            self._finish("failed", f"Could not start {Path(cmd[0]).name}: {exc}")
            return None
        with self._lock:
            self._proc = proc
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        splitter = StreamSplitter()
        while True:
            chunk = proc.stdout.read1(4096)
            if not chunk:
                break
            self._consume(splitter.feed(decoder.decode(chunk)))
        self._consume(splitter.feed(decoder.decode(b"", final=True)) + splitter.flush())
        code = proc.wait()
        with self._lock:
            self._proc = None
            self._job.exit_code = code
            self._job.progress = ""
            cancelled = self._cancelled
        if cancelled:
            self._finish("cancelled", "Cancelled.")
            return None
        return code

    def _consume(self, parts: list[tuple[str, str]]) -> None:
        for kind, text in parts:
            if kind == "progress":
                with self._lock:
                    self._job.progress = text.strip()
            else:
                self._append(text)

    def _append(self, line: str) -> None:
        with self._lock:
            self._job.log.append(line)

    def _finish(self, state: str, message: str) -> None:
        with self._lock:
            self._job.state = state
            self._job.message = message
            self._job.progress = ""


runner = ExtractRunner()
