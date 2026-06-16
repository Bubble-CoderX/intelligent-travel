import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# 后端启动时间戳，前端据此判断是否需要重置暗色模式
_STARTUP_TS = int(time.time())

from app.api.chat import router as chat_router
from app.api.memory import router as memory_router
from app.api.sessions import router as sessions_router
from app.api.trip import router as trip_router
from app.api.weather import router as weather_router
from app.api.proactive import router as proactive_router
from app.api.knowledge import router as knowledge_router
from app.api.weather_intel import router as weather_intel_router
from app.api.trip_history import router as trip_history_router, init_trip_history
from app.api.chat_history import router as chat_history_router
from app.api.weather_records import router as weather_records_router
from app.api.knowledge_browse import router as knowledge_browse_router
from app.models.database import init_db
from app.services.proactive_service import register_ws, unregister_ws, start_scheduler, shutdown_scheduler
from app.services.rag_service import load_knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_trip_history()
    load_knowledge_base()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="TravelMate API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Device-ID"],
)

app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(sessions_router)
app.include_router(trip_router)
app.include_router(weather_router)
app.include_router(proactive_router)
app.include_router(knowledge_router)
app.include_router(weather_intel_router)
app.include_router(trip_history_router)
app.include_router(chat_history_router)
app.include_router(weather_records_router)
app.include_router(knowledge_browse_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/startup-ts")
async def startup_ts():
    return {"startup_ts": _STARTUP_TS}


@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    register_ws(device_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        unregister_ws(device_id)
