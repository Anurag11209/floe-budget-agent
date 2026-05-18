import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server starting...")

    # initialize database tables
    await init_db()

    yield

    print("Server shutting down...")


app = FastAPI(
    title="Floe Budget Agent",
    lifespan=lifespan
)

# Include routes
try:
    from app.api.routes.tasks import router as tasks_router
    app.include_router(tasks_router)
except Exception as e:
    print(f"Warning: Could not load tasks router: {e}")


@app.get("/health")
async def health():
    return {"status": "ok"}