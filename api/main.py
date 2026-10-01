import os
import secrets
import socket
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.auth import ASSETS_PREFIX, TokenAuthMiddleware
from api.shutdown import watch_parent
from api.routes import status, data, ws, setup, capture, rescue, scoring, combatants, optimize, about, autoscroll, simulate, cards, battle, deck_builder, game_data_extract

# Tauri generates this and passes it in, so it never has to be read back off our stdout. Unset means
# "make one up", which is what happens when running standalone. An explicit empty value turns the
# check off and is only used by the test suite.
API_TOKEN = os.environ.get("HUB_CZN_API_TOKEN", secrets.token_urlsafe(32))


def _assets_dir() -> Path:
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'assets'
    return Path(__file__).parent / 'assets'


def create_app(token: str | None = None) -> FastAPI:
    """
    Build the app.

    Args:
        token: API token to require. Defaults to the module-level one.

    Returns:
        The configured FastAPI app.
    """
    app = FastAPI(title="Hub CZN API", version="1.0.0")
    # Order matters: CORS is added last so it ends up outermost and can answer preflight OPTIONS
    # requests, which carry no token.
    app.add_middleware(TokenAuthMiddleware, token=API_TOKEN if token is None else token)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    assets_dir = _assets_dir()
    if assets_dir.exists():
        app.mount(ASSETS_PREFIX, StaticFiles(directory=str(assets_dir)), name="assets")

    app.include_router(status.router, prefix="/api", tags=["status"])
    app.include_router(data.router, prefix="/api", tags=["data"])
    app.include_router(ws.router)
    app.include_router(setup.router, prefix="/api", tags=["setup"])
    app.include_router(capture.router, prefix="/api", tags=["capture"])
    app.include_router(rescue.router, prefix="/api", tags=["rescue"])
    app.include_router(scoring.router, prefix="/api", tags=["scoring"])
    app.include_router(combatants.router, prefix="/api", tags=["combatants"])
    app.include_router(optimize.router, prefix="/api", tags=["optimize"])
    app.include_router(about.router, prefix="/api", tags=["about"])
    app.include_router(autoscroll.router, prefix="/api", tags=["autoscroll"])
    app.include_router(simulate.router, prefix="/api", tags=["simulate"])
    app.include_router(cards.router, prefix="/api", tags=["cards"])
    app.include_router(battle.router, prefix="/api", tags=["battle"])
    app.include_router(deck_builder.router, prefix="/api", tags=["deck-builder"])
    app.include_router(game_data_extract.router, prefix="/api", tags=["game-data"])
    return app


app = create_app()


def _find_free_port(start: int = 7842) -> int:
    for port in range(start, start + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port available in range 7842-7851")


def _chosen_port() -> int:
    """
    Use the port Tauri picked for us, so it does not have to read one back off our stdout.

    Returns:
        The port from HUB_CZN_PORT, or one we pick ourselves when running standalone.
    """
    env_port = os.environ.get("HUB_CZN_PORT", "").strip()
    if env_port.isdigit():
        return int(env_port)
    return _find_free_port()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        # Used by the uninstaller. Undoes a capture that is still in place, then exits.
        from api.shutdown import cleanup
        cleanup()
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        from hub_czn_version import __version__
        print(__version__, flush=True)
        sys.exit(0)
    # Tauri does not kill us any more, so a capture gets undone properly when the window closes.
    watch_parent()
    try:
        port = _chosen_port()
        print(f"PORT:{port}", flush=True)
        print(f"TOKEN:{API_TOKEN}", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    except Exception as exc:
        print(f"ERROR:{exc}", flush=True, file=sys.stderr)
        sys.exit(1)
