import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import client_db
from api import game_data_extract as extract
from api.main import app

client = TestClient(app)

# Stands in for ChaosZeroNightmareRipper-CLI.exe. Prints a \r progress bar, writes the requested folders, and exits with FAKE_CLI_EXIT.
FAKE_CLI = r'''
import os, sys
args = sys.argv[1:]
out = args[args.index("--out") + 1]
folders = [args[i + 1] for i, a in enumerate(args) if a == "--folder"]
for i, folder in enumerate(folders):
    sys.stdout.write(f"[{i + 1}/{len(folders)}] {folder}\r")
    sys.stdout.flush()
if os.environ.get("FAKE_CLI_WRITE", "1") == "1":
    for folder in folders:
        os.makedirs(os.path.join(out, folder), exist_ok=True)
    open(os.path.join(out, "text", "en", "text.json"), "w").write("[]")
print("Extracted " + str(len(folders)) + " folders")
sys.exit(int(os.environ.get("FAKE_CLI_EXIT", "0")))
'''


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point the settings file at a temp folder and give each test its own runner."""
    monkeypatch.setattr(client_db, "SETTINGS_FILE", tmp_path / "settings" / "game_data_extract.json")
    monkeypatch.setattr(extract, "runner", extract.ExtractRunner())
    monkeypatch.setattr(extract, "_read_display_icon", lambda: None)
    monkeypatch.setattr(extract, "DEFAULT_BIN", tmp_path / "no-game" / "bin")
    monkeypatch.delenv(client_db.ENV_VAR, raising=False)
    return tmp_path


@pytest.fixture
def fake_setup(isolated, monkeypatch):
    """Save settings pointing at a fake CLI, a fake pack, and a temp output folder."""
    script = isolated / "fake_cli.py"
    script.write_text(FAKE_CLI, encoding="utf-8")
    bat = isolated / "czn-cli.bat"
    bat.write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    pack = isolated / "data.pack"
    pack.write_bytes(b"")
    out = isolated / "out"
    extract.save_settings({"cli_path": str(bat), "pack_path": str(pack), "out_dir": str(out)})
    monkeypatch.setattr(extract, "is_dev_mode", lambda: False)
    return out


def _wait(runner, timeout=30.0):
    deadline = time.monotonic() + timeout
    while runner.is_running():
        assert time.monotonic() < deadline, "job did not finish"
        time.sleep(0.05)
    return runner.snapshot()


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Detection


@pytest.mark.parametrize("icon", [
    r"C:\Games\CZN\bin\loader.exe,0",
    r'"C:\Games\CZN\bin\loader.exe",0',
    r"C:\Games\CZN\bin\loader.exe",
])
def test_bin_from_display_icon(icon):
    assert extract.bin_from_display_icon(icon) == Path(r"C:\Games\CZN\bin")


def test_bin_from_empty_display_icon():
    assert extract.bin_from_display_icon("") is None


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_detect_finds_the_legacy_data_pack(isolated, monkeypatch):
    pack = _touch(isolated / "game" / "bin" / "appdata" / "cznlive" / "data.pack")
    monkeypatch.setattr(extract, "_read_display_icon", lambda: f"{isolated / 'game' / 'bin' / 'loader.exe'},0")
    assert extract.detect_pack_path() == pack


def test_detect_prefers_the_manifest_over_data_pack(isolated, monkeypatch):
    _touch(isolated / "game" / "bin" / "appdata" / "cznlive" / "data.pack")
    manifest = _touch(isolated / "game" / "bin" / "appdata" / "cznlive" / "gameres" / "manifest.ssra")
    monkeypatch.setattr(extract, "_read_display_icon", lambda: f"{isolated / 'game' / 'bin' / 'loader.exe'},0")
    assert extract.detect_pack_path() == manifest


def test_detect_falls_back_to_default_path(isolated, monkeypatch):
    default_bin = isolated / "default" / "bin"
    manifest = _touch(default_bin / "appdata" / "cznlive" / "gameres" / "manifest.ssra")
    monkeypatch.setattr(extract, "DEFAULT_BIN", default_bin)
    monkeypatch.setattr(extract, "_read_display_icon", lambda: r"C:\nowhere\bin\loader.exe,0")
    assert extract.detect_pack_path() == manifest


def test_detect_returns_none_when_nothing_exists(isolated):
    assert extract.detect_pack_path() is None


def test_a_saved_pack_that_moved_falls_back_to_detection(isolated, monkeypatch):
    manifest = _touch(isolated / "game" / "bin" / "appdata" / "cznlive" / "gameres" / "manifest.ssra")
    monkeypatch.setattr(extract, "_read_display_icon", lambda: f"{isolated / 'game' / 'bin' / 'loader.exe'},0")
    extract.save_settings({"pack_path": str(isolated / "game" / "bin" / "appdata" / "cznlive" / "data.pack")})
    assert extract.load_settings()["pack_path"] == str(manifest)


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Settings and client DB resolution


def test_settings_defaults_and_round_trip(isolated):
    settings = extract.load_settings()
    assert settings["cli_path"] == ""
    assert settings["pack_path"] == ""
    assert settings["out_dir"] == str(client_db.REPO_ROOT / "client_db")
    saved = extract.save_settings({"cli_path": r"C:\tools\czn-cli.exe", "out_dir": None})
    assert saved["cli_path"] == r"C:\tools\czn-cli.exe"
    assert json.loads(client_db.SETTINGS_FILE.read_text()) == {"cli_path": r"C:\tools\czn-cli.exe"}


def test_default_extract_dir_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(client_db, "APP_DIR", Path(r"C:\Users\me\AppData\Local\hub-czn"))
    assert client_db.default_extract_dir() == Path(r"C:\Users\me\AppData\Local\hub-czn\client_db")
    assert extract.is_dev_mode() is False


def test_frozen_app_reads_the_default_folder_with_nothing_saved(isolated, monkeypatch):
    # The installed app extracts into its own folder when the user keeps the default, so it must also read from there.
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(client_db, "APP_DIR", isolated / "install")
    (isolated / "install" / "client_db" / "db").mkdir(parents=True)
    extract.save_settings({"cli_path": r"C:\tools\cli.exe"})
    assert client_db.client_output_dir() == isolated / "install" / "client_db"


def test_client_output_dir_priority(isolated, monkeypatch):
    repo = isolated / "repo"
    (repo / "client_db").mkdir(parents=True)
    monkeypatch.setattr(client_db, "REPO_ROOT", repo)
    saved = isolated / "saved"
    extract.save_settings({"out_dir": str(saved)})

    # A saved folder with no db/ yet is skipped in favour of the repo folder.
    assert client_db.client_output_dir() == repo / "client_db"
    (saved / "db").mkdir(parents=True)
    assert client_db.client_output_dir() == saved
    monkeypatch.setenv(client_db.ENV_VAR, str(isolated / "env"))
    assert client_db.client_output_dir() == isolated / "env"


def test_reset_caches_drops_the_eff_index(monkeypatch):
    from api.game_data import char_eff
    monkeypatch.setattr(char_eff, "_DEFAULT_EFF_INDEX", object())
    client_db.reset_caches()
    assert char_eff._DEFAULT_EFF_INDEX is None


def test_cs_multiplier_index_reads_the_current_folder(isolated, monkeypatch):
    from api.game_data.cs_multipliers import CSMultiplierIndex
    monkeypatch.setenv(client_db.ENV_VAR, str(isolated / "first"))
    assert CSMultiplierIndex()._db_path == isolated / "first" / "db"
    monkeypatch.setenv(client_db.ENV_VAR, str(isolated / "second"))
    assert CSMultiplierIndex()._db_path == isolated / "second" / "db"


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Output handling


def test_splitter_separates_progress_from_lines():
    s = extract.StreamSplitter()
    parts = s.feed("[1/4] db\r[2/4] face\rDone\r")
    # The trailing \r is held back in case \n follows.
    assert parts == [("progress", "[1/4] db"), ("progress", "[2/4] face")]
    assert s.feed("\nnext") == [("line", "Done")]
    assert s.flush() == [("line", "next")]


def test_czn_cli_percentage_lines_go_to_progress():
    parts = extract.StreamSplitter().feed("[1/4] db\n  Extracting 35% total 12%\nScanning 100%\nDone.\n")
    assert parts == [("line", "[1/4] db"), ("progress", "  Extracting 35% total 12%"), ("progress", "Scanning 100%"), ("line", "Done.")]


def test_log_keeps_the_last_lines():
    job = extract.Job(kind="extract")
    job.log.extend(str(i) for i in range(extract.LOG_LIMIT + 5))
    assert job.to_dict()["log"][0] == "5"


def test_splitter_drops_blank_progress():
    assert extract.StreamSplitter().feed("\r   \rline\n") == [("line", "line")]


@pytest.mark.parametrize("code,fragment", [(0, "all four"), (2, "open or scan"), (3, "czn_ripper.log"), (4, "None of"), (9, "code 9")])
def test_exit_messages(code, fragment):
    assert fragment in extract.exit_message(code)


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Running the CLI


def test_extract_success(fake_setup):
    extract.runner.start_extract()
    job = _wait(extract.runner)
    assert job["state"] == "ok", job
    assert job["exit_code"] == 0
    assert "Extracted 4 folders" in job["log"]
    assert (fake_setup / "db").is_dir()
    assert (fake_setup / "tp_skill").is_dir()


def test_extract_maps_exit_code(fake_setup, monkeypatch):
    monkeypatch.setenv("FAKE_CLI_EXIT", "3")
    extract.runner.start_extract()
    job = _wait(extract.runner)
    assert job["state"] == "failed"
    assert job["exit_code"] == 3
    assert "czn_ripper.log" in job["message"]


def test_extract_fails_when_output_is_incomplete(fake_setup, monkeypatch):
    monkeypatch.setenv("FAKE_CLI_WRITE", "0")
    extract.runner.start_extract()
    job = _wait(extract.runner)
    assert job["state"] == "failed"
    assert "db/" in job["message"] and "text.json" in job["message"]


def test_extract_in_dev_mode_chains_a_dry_run(fake_setup, monkeypatch):
    script = fake_setup.parent / "fake_add_character.py"
    script.write_text("import sys\nprint('args:', ' '.join(sys.argv[1:]))\n", encoding="utf-8")
    monkeypatch.setattr(extract, "ADD_CHARACTER_SCRIPT", script)
    monkeypatch.setattr(extract, "is_dev_mode", lambda: True)
    extract.runner.start_extract()
    job = _wait(extract.runner)
    assert job["state"] == "ok", job
    assert job["kind"] == "dry_run"
    assert f"args: {fake_setup} --dry-run" in job["log"]


def test_start_without_cli_is_a_400(isolated):
    r = client.post("/api/game-data/extract/start")
    assert r.status_code == 400
    assert "ChaosZeroNightmareRipper-CLI" in r.json()["detail"]


def test_second_start_is_a_409(fake_setup, monkeypatch):
    monkeypatch.setattr(extract.ExtractRunner, "is_running", lambda self: True)
    with extract.runner._lock:
        extract.runner._job = extract.Job(kind="extract")
    assert client.post("/api/game-data/extract/start").status_code == 409
    assert client.post("/api/game-data/extract/config", json={"out_dir": "x"}).status_code == 409


def test_status_shape(fake_setup):
    body = client.get("/api/game-data/extract/status").json()
    assert body["settings"]["out_dir"] == str(fake_setup)
    assert body["dev_mode"] is False
    assert body["job"] is None
    assert {"detected_pack_path", "env_override", "active_client_dir", "active_ready"} <= body.keys()


def test_apply_is_404_outside_dev_mode(isolated, monkeypatch):
    monkeypatch.setattr(extract, "is_dev_mode", lambda: False)
    assert client.post("/api/game-data/apply", json={"dry_run": True}).status_code == 404
