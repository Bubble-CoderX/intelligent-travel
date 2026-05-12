from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.memory import router as memory_router
from app.api.sessions import router as sessions_router
from app.api.trip import router as trip_router
from app.api.weather import router as weather_router
from app.api.proactive import router as proactive_router
from app.api.knowledge import router as knowledge_router
from app.models.database import init_db
from app.services.proactive_service import register_ws, unregister_ws, start_scheduler, shutdown_scheduler
from app.services.rag_service import load_knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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


@app.get("/health")
async def health():
    return {"status": "ok"}


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
