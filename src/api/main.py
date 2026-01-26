from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from ..core.scheduler import start_scheduler, stop_scheduler
from contextlib import asynccontextmanager

import socket
import logging

logger = logging.getLogger("uvicorn")

# Global socket lock to hold ownership of "Leader" status
# Must be global to persist during lifespan yield
leader_socket = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global leader_socket
    is_leader = False
    
    try:
        # Try to acquire Leader Lock by binding a dedicated port
        # This auto-releases when process exits, handling restarts gracefully.
        leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        leader_socket.bind(("127.0.0.1", 18888))
        is_leader = True
        logger.info("Instance acquired Leadership (Port 18888 locked). Scheduler active.")
    except OSError:
        is_leader = False
        logger.warning("Instance is Standby (Leader lock held by another process). Scheduler/Headbeats disabled.")
        
    if is_leader:
        # Only Leader runs background jobs and logs startup
        start_scheduler()
        from src.core.monitoring import monitor
        monitor.log_heartbeat("SystemStartup", "success", {"message": "API started"})
        # 2. Cleanup Stale Tasks
        monitor.check_stale_tasks()
    
    yield
    
    if is_leader:
        stop_scheduler()
        if leader_socket:
            leader_socket.close()

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
@app.head("/")
def root():
    return {"status": "ok", "message": "Antigravity API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
