from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .routers import users, libraries, dashboard
import os

app = FastAPI(title="Emby Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(libraries.router)
app.include_router(dashboard.router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
FRONTEND_PATH = os.path.join(STATIC_DIR, "index.html")

app.mount("/lib", StaticFiles(directory=os.path.join(STATIC_DIR, "lib")), name="lib")

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/")
@app.get("/{path:path}")
async def spa(path: str = ""):
    if path.startswith("api/") or path.startswith("lib/"):
        return {"error": "not found"}
    return FileResponse(FRONTEND_PATH)
