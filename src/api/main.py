from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from ..core.scheduler import start_scheduler, stop_scheduler
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    from src.core.monitoring import monitor
    monitor.log_heartbeat("SystemStartup", "success", {"message": "API started"})
    # 2. Cleanup Stale Tasks (from previous crashes/redeployments)
    monitor.check_stale_tasks()
    yield
    # Shutdown
    stop_scheduler()

app = FastAPI(title="Antigravity API", lifespan=lifespan)

# CORS
# We need to allow Vercel Previews, which use dynamic subdomains.
# Using allow_origin_regex for flexibility.
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://forcust-tool-antigravity.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app", # Allow all Vercel subdomains (Previews)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {"status": "ok", "message": "Antigravity API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
