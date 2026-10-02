from __future__ import annotations

import os
from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import client_db
from api import game_data_extract as extract

router = APIRouter()


class ExtractConfigRequest(BaseModel):
    """Path changes from the Setup page. A field left out keeps its saved value."""

    # Full path to ChaosZeroNightmareRipper-CLI.exe.
    cli_path: str | None = None
    # Full path to the game's archive, `manifest.ssra` or the older `data.pack`.
    pack_path: str | None = None
    # Folder the four client folders are extracted into.
    out_dir: str | None = None


class ApplyRequest(BaseModel):
    """Options for running add_character.py against the extraction."""

    # Pass --dry-run so nothing is written.
    dry_run: bool = True


def _start(begin: Callable[[], None]) -> dict:
    """
    Start a job, mapping the runner's refusals to HTTP errors.

    Args:
        begin: The runner method call that starts the job.

    Returns:
        `{"ok": True}` once the job is running.

    Raises:
        HTTPException: 409 when a job is already running, 400 when a path is missing.
    """
    try:
        begin()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


@router.get("/game-data/extract/status")
def extract_status():
    detected = extract.detect_pack_path()
    active = client_db.client_output_dir()
    return {
        "settings": extract.load_settings(detected),
        "detected_pack_path": str(detected) if detected else None,
        "dev_mode": extract.is_dev_mode(),
        "env_override": os.environ.get(client_db.ENV_VAR, "").strip() or None,
        "active_client_dir": str(active),
        "active_ready": not extract.missing_output(active),
        "job": extract.runner.snapshot(),
    }


@router.post("/game-data/extract/config")
def save_extract_config(body: ExtractConfigRequest):
    if extract.runner.is_running():
        raise HTTPException(status_code=409, detail="An extraction is running.")
    return extract.save_settings(body.model_dump())


@router.post("/game-data/extract/start")
def start_extract():
    return _start(extract.runner.start_extract)


@router.post("/game-data/extract/cancel")
def cancel_extract():
    return {"ok": extract.runner.cancel()}


@router.post("/game-data/apply")
def apply_characters(body: ApplyRequest):
    if not extract.is_dev_mode():
        raise HTTPException(status_code=404, detail="Only available when running from source.")
    return _start(lambda: extract.runner.start_apply(body.dry_run))
