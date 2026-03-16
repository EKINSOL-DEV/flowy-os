"""
Main FastAPI application that dynamically loads all cogs in ./cogs/*_cog.py
and mounts their routers.
"""

import importlib
import pkgutil
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Ensure cogs package is importable
COGS_PATH = Path(__file__).parent / "cogs"
if str(COGS_PATH.parent) not in sys.path:
    sys.path.append(str(COGS_PATH.parent))

# Turn directory into a package
(COGS_PATH / "__init__.py").write_text("# auto-generated package marker\n")

def load_cogs(app: FastAPI):
    package_name = "cogs"
    package = importlib.import_module(package_name)
    for m in pkgutil.iter_modules([str(COGS_PATH)]):
        name = m.name
        if not name.endswith("_cog"):
            continue
        module = importlib.import_module(f"{package_name}.{name}")
        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router)

def create_app() -> FastAPI:
    app = FastAPI(title="Flowy Unified API", version="1.0.0")

    # Open CORS by default (adjust as needed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    load_cogs(app)
    
    # Serve NFC test page
    @app.get("/nfc-test", response_class=HTMLResponse)
    async def nfc_websocket_test():
        static_file = Path(__file__).parent / "static" / "nfc_websocket_test.html"
        if static_file.exists():
            return HTMLResponse(content=static_file.read_text())
        return HTMLResponse(content="<h1>Test page not found</h1>", status_code=404)

    # Serve Companion PWA
    companion_dir = Path(__file__).parent / "static" / "companion"
    if companion_dir.exists():
        app.mount("/companion", StaticFiles(directory=str(companion_dir), html=True), name="companion")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn, os
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("main_api:app", host="0.0.0.0", port=port, reload=os.getenv("ENVIRONMENT")=="development", log_level="debug")
