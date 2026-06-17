# AI智游伴 (TravelMate) 项目书

> **项目名称**：AI智游伴 (TravelMate) — 智能旅行对话助手
> **文档版本**：v1.0（整合版，合并完整实现方案与优化方案）
> **最后更新**：2026-05-13

---

## 目录

- [一、项目概述](#一项目概述)
- [二、系统架构](#二系统架构)
- [三、数据流与工作流程](#三数据流与工作流程)
- [四、基础实现：工程搭建与界面（阶段0-2）](#四基础实现工程搭建与界面阶段0-2)
- [五、核心智能层：意图识别与记忆系统（阶段3-4）](#五核心智能层意图识别与记忆系统阶段3-4)
- [六、外部集成与知识服务（阶段5-7）](#六外部集成与知识服务阶段5-7)
- [七、主动服务与安全体系（阶段8-10）](#七主动服务与安全体系阶段8-10)
- [八、增强功能与部署（阶段11-12）](#八增强功能与部署阶段11-12)
- [九、优化升级方案](#九优化升级方案)
- [十、附录](#十附录)

---

## 一、项目概述

### 1.1 项目定位

**AI智游伴 (TravelMate)** 是一款基于大语言模型的智能旅行对话助手，集行程规划、景点讲解、天气查询、偏好记忆于一体。用户通过自然语言对话即可获得个性化的旅行建议和完整的行程方案。

### 1.2 核心能力

| 能力 | 说明 |
|------|------|
| 行程规划 | 基于用户偏好、实时 POI、天气数据，LLM 生成结构化多日行程方案 |
| 景点知识 | RAG 知识检索 + LLM 导游式回答，支持自动调研扩充知识库 |
| 天气查询 | 实时天气预报与穿衣建议 |
| 偏好记忆 | 双引擎记忆系统（向量 + 结构化），记住用户饮食、预算、出行偏好 |
| 主动服务 | 定时天气提醒、到达景点问候、个性化开场白 |
| 安全防护 | 三级安全检查（拦截/警告/紧急），输入输出双向过滤 |
| 语音交互 | 语音识别 + TTS 播报景点知识 |

### 1.3 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端框架** | Vue 3 + TypeScript + Vite | 组合式 API，类型安全 |
| **状态管理** | Pinia | 响应式状态，支持热重载 |
| **样式** | Tailwind CSS v4 | CSS-first 配置，暗色模式支持 |
| **HTTP 客户端** | Axios | 统一拦截器，baseURL 配置 |
| **后端框架** | FastAPI | 异步高性能，自动 OpenAPI 文档 |
| **结构化存储** | SQLite | 会话、消息、偏好、行程数据 |
| **向量存储** | ChromaDB | 语义相似度搜索（用户偏好 + 知识库） |
| **LLM** | DeepSeek | 意图识别、行程生成、知识问答、问候生成 |
| **地图服务** | 高德地图 API | POI 搜索、地理编码、天气查询 |
| **知识搜索** | DuckDuckGo | 免费网络搜索，用于知识库自动调研 |
| **实时通信** | WebSocket | 主动消息推送 |
| **定时任务** | APScheduler | 轻量级异步定时任务 |
| **语音** | Web Speech API | 浏览器端语音识别 + TTS |

### 1.4 功能全景图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI智游伴 功能全景                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  行程规划    │  │  景点知识    │  │  天气查询    │                │
│  │  ·多日行程   │  │  ·RAG检索   │  │  ·实时预报   │                │
│  │  ·风格对比   │  │  ·自动调研   │  │  ·穿衣建议   │                │
│  │  ·预算估算   │  │  ·反馈纠正   │  │  ·出行提醒   │                │
│  │  ·准备清单   │  │  ·导游问答   │  │  ·首页天气   │                │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                │
│         │                │                │                         │
│  ┌──────┴────────────────┴────────────────┴──────┐                │
│  │              三级意图识别管道                     │                │
│  │  正则匹配 → AI 意图识别 → 安全检查               │                │
│  └──────┬────────────────┬────────────────┬──────┘                │
│         │                │                │                         │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐                │
│  │  偏好记忆    │  │  会话管理    │  │  主动服务    │                │
│  │  ·双引擎    │  │  ·多会话     │  │  ·天气提醒   │                │
│  │  ·语义搜索  │  │  ·自动命名   │  │  ·智能问候   │                │
│  │  ·上下文注入│  │  ·重命名     │  │  ·到达欢迎   │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  安全防护    │  │  语音交互    │  │  界面美化    │                │
│  │  ·三级检查   │  │  ·语音识别   │  │  ·暗色模式   │                │
│  │  ·输入过滤   │  │  ·TTS播报   │  │  ·暖色主题   │                │
│  │  ·输出过滤   │  │  ·普通话     │  │  ·微动画     │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.5 核心代码示例：应用入口

**后端入口** `backend/app/main.py`：

```python
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# 后端启动时间戳，前端据此判断是否需要重置暗色模式
_STARTUP_TS = int(time.time())

from app.api.chat import router as chat_router
from app.api.sessions import router as sessions_router
from app.models.database import init_db
from app.services.proactive_service import register_ws, unregister_ws, start_scheduler
from app.services.rag_service import load_knowledge_base

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()               # 初始化数据库 + 增量迁移
    load_knowledge_base()    # 加载景点知识到 ChromaDB
    start_scheduler()        # 启动 APScheduler 定时任务
    yield
    shutdown_scheduler()

app = FastAPI(title="TravelMate API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由
app.include_router(chat_router)
app.include_router(sessions_router)
# ... 其他路由

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
```

**前端入口** `frontend/src/App.vue`（暗色模式 + 后端重启检测）：

```typescript
<script setup lang="ts">
import { ref, onMounted, watchEffect } from 'vue'
import ChatContainer from '@/components/chat/ChatContainer.vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { getDeviceId } from '@/utils/device'

const { connected } = useWebSocket(getDeviceId())
const API_BASE = 'http://localhost:8000'

// 同步初始化：读 localStorage → 系统偏好 → 默认浅色
function initDark(): boolean {
  const stored = localStorage.getItem('travelmate_dark')
  const storedTs = localStorage.getItem('travelmate_startup_ts')
  if (stored !== null && storedTs !== null) {
    return stored === 'true'
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const dark = ref(initDark())

watchEffect(() => {
  document.documentElement.classList.toggle('dark', dark.value)
  localStorage.setItem('travelmate_dark', String(dark.value))
})

// 启动后校验后端是否重启：重启则清除暗色偏好
onMounted(async () => {
  try {
    const res = await fetch(`${API_BASE}/startup-ts`)
    if (!res.ok) return
    const { startup_ts } = await res.json()
    const storedTs = localStorage.getItem('travelmate_startup_ts')
    if (storedTs !== null && String(startup_ts) !== storedTs) {
      dark.value = false  // 后端重启了 → 强制浅色
    }
    localStorage.setItem('travelmate_startup_ts', String(startup_ts))
  } catch { /* 后端未启动 */ }
})
</script>
```

### 1.6 测试预期与结果

| 测试项 | 操作 | 预期结果 | 实际结果 |
|--------|------|----------|----------|
| 后端启动 | `uvicorn app.main:app` | 日志输出"数据库初始化完成""知识库加载完成" | ✅ 通过 |
| 健康检查 | GET `/health` | 返回 `{"status": "ok"}` | ✅ 通过 |
| 启动时间戳 | GET `/startup-ts` | 返回 `{"startup_ts": <unix时间戳>}` | ✅ 通过 |
| 前端启动 | `npm run dev` | 浏览器打开 localhost:5173 显示聊天界面 | ✅ 通过 |
| CORS 配置 | 前端跨域请求后端 | 无 CORS 错误 | ✅ 通过 |
| WebSocket 连接 | 浏览器连接 `/ws/{device_id}` | 连接成功，ping/pong 正常 | ✅ 通过 |

---

## 二、系统架构

### 2.1 四大系统组件

```mermaid
graph TB
    subgraph "用户设备 (Vue 3 + TypeScript)"
        UI[UI 组件层]
        Store[Pinia 状态管理]
        HTTP[Axios HTTP 客户端]
        WS_Client[WebSocket 客户端]
    end

    subgraph "云服务器 (FastAPI + Python)"
        API[API 网关]
        Intent[意图识别管道]
        Toolbox[Agent 工具箱]
        Proactive[主动服务模块]
    end

    subgraph "外部依赖"
        LLM[DeepSeek LLM API]
        Maps[高德地图 API]
        Search[DuckDuckGo 搜索]
    end

    subgraph "数据存储"
        SQLite[(SQLite 结构化)]
        Chroma[(ChromaDB 向量)]
    end

    UI --> Store
    Store --> HTTP
    HTTP --> API
    WS_Client --> Proactive
    API --> Intent
    Intent --> Toolbox
    Toolbox --> LLM
    Toolbox --> Maps
    Toolbox --> Search
    Toolbox --> SQLite
    Toolbox --> Chroma
```

### 2.2 目录结构

```
travelmate/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口 + 启动时间戳
│   │   ├── config.py            # pydantic-settings 配置管理
│   │   ├── api/
│   │   │   ├── chat.py          # POST /chat 核心端点
│   │   │   ├── sessions.py      # 会话 CRUD API
│   │   │   ├── memory.py        # 偏好管理 API
│   │   │   ├── weather.py       # 天气查询 API
│   │   │   ├── knowledge.py     # 知识库管理 API（自动调研/批量扩充）
│   │   │   ├── proactive.py     # 主动问候 API
│   │   │   └── trip.py          # 行程导出 API
│   │   ├── services/
│   │   │   ├── intent_router.py      # 三级意图识别管道
│   │   │   ├── memory_service.py     # Hermes 记忆系统
│   │   │   ├── context_service.py    # 对话上下文管理
│   │   │   ├── trip_service.py       # 行程生成服务
│   │   │   ├── rag_service.py        # RAG 知识检索服务
│   │   │   ├── knowledge_expander.py # 知识库自动调研管线
│   │   │   ├── weather_service.py    # 天气查询服务
│   │   │   ├── map_service.py        # 高德地图服务
│   │   │   ├── proactive_service.py  # 主动服务逻辑
│   │   │   ├── export_service.py     # 行程导出服务
│   │   │   ├── llm_client.py         # DeepSeek API 封装
│   │   │   └── checklist_service.py  # 旅行准备清单
│   │   ├── models/
│   │   │   ├── database.py     # SQLite 连接 + 表创建 + 迁移
│   │   │   └── schemas.py      # Pydantic 数据模型
│   │   ├── utils/
│   │   │   ├── safety.py       # 安全检查（输入/输出/限流）
│   │   │   ├── trip_prompts.py # 行程生成 Prompt 模板
│   │   │   └── device.py       # 设备 ID 工具
│   │   └── tools/
│   │       └── tool_registry.py # 工具注册中心
│   ├── db/                     # SQLite + ChromaDB 数据目录
│   │   ├── travelmate.db
│   │   ├── chroma_memory/      # 用户偏好向量库
│   │   └── chroma_knowledge/   # 景点知识向量库
│   ├── data/knowledge/         # 景点知识 Markdown 文档
│   ├── requirements.txt
│   └── .env                    # API Keys（不入 Git）
│
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue             # 暗色模式管理 + 后端重启检测
│   │   ├── style.css           # Tailwind v4 + 暗色模式变体
│   │   ├── api/
│   │   │   └── client.ts       # Axios 实例 + 拦截器
│   │   ├── stores/
│   │   │   └── chat.ts         # Pinia 聊天状态管理
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatContainer.vue   # 主布局（侧边栏+消息区）
│   │   │   │   ├── ChatInput.vue       # 输入框 + 风格选择器
│   │   │   │   ├── MessageBubble.vue   # 消息气泡 + Markdown
│   │   │   │   ├── TripCard.vue        # 结构化行程卡片
│   │   │   │   ├── SessionSidebar.vue  # 会话侧边栏
│   │   │   │   ├── StyleSelector.vue   # 行程风格选择器
│   │   │   │   ├── PreferencePanel.vue # 偏好管理面板
│   │   │   │   ├── BatchExpandModal.vue# 知识库批量扩充
│   │   │   │   └── WelcomePage.vue     # 欢迎页
│   │   │   └── common/
│   │   │       └── icons/
│   │   ├── composables/
│   │   │   ├── useWebSocket.ts    # WebSocket 连接管理
│   │   │   ├── useSpeechRecognition.ts # 语音识别
│   │   │   └── useSpeechSynthesis.ts   # TTS 播报
│   │   ├── utils/
│   │   │   ├── device.ts      # 设备 ID 生成
│   │   │   └── format.ts      # 时间格式化
│   │   └── types/
│   │       └── index.ts       # 全局 TypeScript 类型
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── package.json
│
├── docs/                        # 项目文档
│   ├── AI智游伴项目书.md         # 本文档
│   ├── optimization-plan.md     # 优化方案（详细实施）
│   └── project-progress.md      # 开发进度记录
│
└── README.md
```

### 2.3 核心数据结构

#### 2.3.1 前端消息模型

```typescript
interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  type: 'text' | 'card' | 'weather' | 'knowledge' | 'proactive'
  metadata?: {
    trip_plan?: Itinerary      // 结构化行程数据
    trip_style?: string        // compact/leisure/culture
    destination?: string
    days?: number
    safety_warning?: string
    layer?: string             // regex/ai
    sub_intent?: string
    confidence?: number
    proactive_type?: string    // greeting
    quick_actions?: QuickAction[]
  }
}
```

#### 2.3.2 后端 Pydantic 模型

```python
class ChatRequest(BaseModel):
    message: str                  # 用户输入
    device_id: str                # 设备唯一标识
    session_id: str | None        # 会话 ID
    trip_style: str | None        # 行程风格

class ChatResponse(BaseModel):
    reply: str                    # AI 回复文本
    intent: str                   # 识别到的意图
    message_type: str             # 展示类型：text/card/weather/knowledge
    metadata: dict | None         # 附加数据（行程、安全等）

class Itinerary(BaseModel):
    trip_id: str
    destination: str
    summary: str
    days: list[DayPlan]
    estimated_budget: int
    budget_breakdown: BudgetBreakdown
    tips: list[str]
    food_summary: str
    transport_summary: str
    accommodation_summary: str

class DayPlan(BaseModel):
    day_index: int
    theme: str
    spots: list[SpotItem]
    meals: list[MealItem]
    transport: list[TransportItem]
    hotel: HotelItem | None
```

#### 2.3.3 数据库 Schema（SQLite）

```sql
-- 设备表
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会话表
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    title TEXT DEFAULT '新会话',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对话消息表
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,              -- user/assistant/system
    content TEXT NOT NULL,
    intent TEXT,                     -- 识别到的意图分类
    metadata TEXT,                   -- JSON 附加数据（行程/天气等）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户偏好表
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    category TEXT NOT NULL,          -- 饮食/出行/住宿/通用
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 0.8,     -- 置信度
    source TEXT DEFAULT 'explicit',  -- explicit/inferred
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 行程规划表
CREATE TABLE trip_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    destination TEXT NOT NULL,
    days INTEGER,
    plan_json TEXT,                  -- 完整 Itinerary JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.4 核心代码示例：数据库初始化

```python
# backend/app/models/database.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "travelmate.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            title TEXT DEFAULT '新会话',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            intent TEXT,
            metadata TEXT,  -- JSON 附加数据
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 0.8,
            source TEXT DEFAULT 'explicit',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS trip_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            destination TEXT NOT NULL,
            days INTEGER,
            plan_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # 增量迁移：添加 metadata 列
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN metadata TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 列已存在
    conn.close()
```

### 2.5 测试预期与结果

| 测试项 | 操作 | 预期结果 | 实际结果 |
|--------|------|----------|----------|
| 数据库创建 | 启动后端 | `db/travelmate.db` 自动生成，含 5 张表 | ✅ 通过 |
| 增量迁移 | 重复启动 | `metadata` 列不重复添加，无报错 | ✅ 通过 |
| Row 工厂 | 查询返回 `sqlite3.Row` | 可用 `row["column_name"]` 访问 | ✅ 通过 |

---

## 三、数据流与工作流程

### 3.1 完整数据流

```mermaid
flowchart TD
    A[用户输入] --> B[POST /chat]
    B --> C{输入安全检查}
    C -->|BLOCK| D[拒绝回复]
    C -->|PASS/WARN/URGENT| E{正则快速匹配}
    E -->|命中| F[预设回复]
    E -->|未命中| G{AI 意图识别}
    G --> H{意图分类}
    H -->|PREFERENCE| I[保存偏好到记忆系统]
    H -->|TRIP_PLAN| J[行程生成服务]
    H -->|WEATHER| K[天气查询服务]
    H -->|KNOWLEDGE| L[RAG 知识检索]
    H -->|CHAT| M[通用 LLM 对话]
    J --> N[高德 POI + 天气 + 偏好]
    N --> O[LLM 生成结构化 JSON]
    L --> P{知识库检索}
    P -->|命中| Q[LLM 导游式回答]
    P -->|未命中| R[自动调研→入库→重检]
    R --> Q
    F & I & O & K & Q & M --> S{输出安全过滤}
    S --> T[返回 ChatResponse]
    T --> U[保存到 SQLite]
    U --> V[前端渲染]
```

### 3.2 三级意图识别管道

意图识别是系统的核心智能层，采用**正则 + AI + 安全**三层管道设计：

```
用户消息
  ↓
【第一层：正则快速匹配】<10ms
  ├── 问候语（你好/嗨/早上好）
  ├── 告别语（再见/拜拜）
  ├── 感谢语（谢谢/感谢）
  ├── 确认语（好的/可以/没问题）
  └── 50 字限制，超长直接跳过 AI
  ↓
【第二层：AI 意图识别】~300ms
  ├── 注入最近 6 条对话历史（上下文感知）
  ├── 注入用户历史偏好（个性化参考）
  ├── 输出结构化 JSON：
  │   intent / sub_intent / confidence / reasoning / extracted_data
  └── 意图优先级：
      PREFERENCE > 上下文延续 > TRIP_PLAN > WEATHER > KNOWLEDGE > CHAT
  ↓
【第三层：安全检查】
  ├── BLOCK（拦截）：非法活动关键词
  ├── WARN（警告）：高风险场景
  ├── URGENT（紧急）：医疗紧急情况
  └── 输出过滤：确保 AI 不鼓励危险行为
  ↓
返回意图 + 回复 + 安全等级
```

**意图分类体系**：

| 意图类别 | 代码 | 子意图 | 说明 |
|----------|------|--------|------|
| 行程规划 | TRIP_PLAN | trip_create / trip_modify / trip_query | 创建、修改或查询旅行计划 |
| 天气查询 | WEATHER | weather_current / weather_forecast | 查询当前天气或未来天气 |
| 偏好记录 | PREFERENCE | pref_set / pref_query | 用户设置或查询个人偏好 |
| 景点知识 | KNOWLEDGE | spot_intro / spot_nearby / spot_history | 景点介绍、周边查询、历史故事 |
| 闲聊问答 | CHAT | chat_general / chat_travel_tips | 普通对话、旅行小贴士 |

### 3.3 上下文延续机制

意图识别会注入最近 6 条对话历史，确保上下文连续性：

```
用户：查询杭州的天气
助手：杭州今天晴，28°C...
用户：哈尔滨                    ← 无"天气"关键词，但上轮在问天气
  ↓ AI 识别到上下文延续 → WEATHER
助手：哈尔滨今天多云，15°C...   ✅ 正确延续天气意图
```

```
用户：帮我规划去杭州的旅行
助手：好的！你想去杭州玩几天？
用户：三天                      ← 无"杭州"，但上轮在规划杭州
  ↓ AI 识别到上下文延续 → TRIP_PLAN
助手：好的，杭州3日游方案已生成 ✅ 正确延续行程意图
```

### 3.4 核心代码示例：意图识别完整管道

```python
# backend/app/services/intent_router.py（核心函数）
async def route_intent(user_message: str, device_id: str,
                       session_id: str | None = None,
                       trip_style: str | None = None) -> dict:
    """完整意图识别管道：安全检查 → 正则 → AI → 输出过滤"""

    # 0. 输入安全检查
    safety = input_safety_check(user_message)
    if not safety["passed"]:
        return {"intent": "blocked", "reply": "抱歉，我无法处理这类请求。", "safety": safety}

    # 1. 第一层：正则快速匹配
    regex_result = regex_match(user_message)
    if regex_result:
        intent, reply = regex_result
        return {"intent": intent, "reply": reply, "layer": "regex", "safety": safety}

    # 2. 特殊模式拦截：自我介绍/回忆问题 → 直接走 CHAT
    if _INTRO_RE.search(user_message) or _RECALL_RE.search(user_message):
        intent_data = {"intent": "CHAT", "sub_intent": "chat_general",
                       "confidence": 1.0, "extracted_data": {}}
    else:
        # 3. 第二层：AI 意图识别（注入最近 6 条对话历史）
        recent = await get_recent_history(device_id, session_id=session_id, limit=6)
        recent_lines = [f"{'助手' if m['role']=='assistant' else '用户'}：{m['content'][:80]}"
                        for m in recent[-6:]]
        recent_ctx = "\n".join(recent_lines) if recent_lines else "（无历史）"

        intent_prompt = INTENT_RECOGNITION_PROMPT.replace(
            "{user_message}", user_message
        ).replace("{recent_context}", recent_ctx
        ).replace("{user_preferences}", _get_user_preferences(device_id))

        raw_response = await call_llm(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=intent_prompt, temperature=0.1, max_tokens=500,
        )
        try:
            intent_data = json.loads(raw_response)
        except json.JSONDecodeError:
            intent_data = {"intent": "CHAT", "sub_intent": "chat_general",
                           "confidence": 0.5, "extracted_data": {}}

    intent = intent_data.get("intent", "CHAT")
    extracted = intent_data.get("extracted_data", {})

    # 4. PREFERENCE 自动写入记忆
    if intent == "PREFERENCE" and extracted.get("key"):
        save_memory(device_id, extracted.get("category","通用"),
                    extracted["key"], extracted.get("value",""))
        reply = f"好的，已记住你的偏好：{extracted['value']}。"

    # 5. TRIP_PLAN → 行程生成（含上下文补全）
    elif intent == "TRIP_PLAN":
        destination = extracted.get("destination", "")
        if not destination:
            # 从对话历史中补全目的地
            history = await get_recent_history(device_id, session_id=session_id)
            resolved = await call_llm(
                messages=[{"role":"user", "content": f"历史：{hist_text}\n当前：{user_message}"}],
                system_prompt="提取最近提到的旅行目的地，只返回名称，没有返回\"无\"。",
                temperature=0.0, max_tokens=50)
            destination = resolved.strip() if resolved.strip() != "无" else ""

        if not destination:
            reply = "请问你想去哪里旅行呢？"
        elif not extracted.get("days"):
            reply = f"好的，你想去{destination}！请问计划玩几天呢？"
        else:
            result = await generate_trip_plan(device_id, destination,
                                              int(extracted["days"]),
                                              style=trip_style or "default")
            reply = result["summary"]
            extracted["_trip_plan"] = result.get("itinerary_json")

    # 6. WEATHER / KNOWLEDGE / CHAT 各分支...

    # 输出安全过滤
    reply = await filter_llm_output(reply)
    return {"intent": intent, "reply": reply, "layer": "ai", "safety": safety}
```

### 3.5 测试预期与结果

| 测试场景 | 输入 | 预期意图 | 预期回复 | 实际结果 |
|----------|------|----------|----------|----------|
| 简单问候 | "你好" | CHAT（正则） | 预设问候语 | ✅ <10ms |
| 告别 | "再见" | CHAT（正则） | 预设告别语 | ✅ <10ms |
| 行程规划（完整） | "帮我规划杭州3天旅行" | TRIP_PLAN | 询问天数或生成行程 | ✅ |
| 行程规划（上下文延续） | 用户先说"杭州"再说"三天" | TRIP_PLAN | 生成杭州3日行程 | ✅ |
| 天气查询 | "今天天气怎么样" | WEATHER | 询问城市 | ✅ |
| 天气上下文延续 | 聊完天气后说"哈尔滨" | WEATHER | 哈尔滨天气 | ✅ |
| 偏好设置 | "我不吃辣" | PREFERENCE | "已记住你的偏好" | ✅ 已写入记忆 |
| 景点知识 | "西湖有什么历史" | KNOWLEDGE | 导游式回答 | ✅ |
| 纠正信息 | "不对，灵隐寺是东晋建的" | CHAT→纠正 | "已更新知识记录" | ✅ |
| 安全拦截 | "怎么偷门票" | blocked | "无法处理" | ✅ |
| 安全警告 | "一个人去无人区" | WARN | 回复+安全提醒 | ✅ |
| 个人信息 | "你叫什么名字" | CHAT | AI 自我介绍 | ✅ 不存为偏好 |

---

## 四、基础实现：工程搭建与界面（阶段0-2）

### 4.1 阶段零：工程脚手架搭建与基础设施

#### 4.1.1 前端初始化

```bash
# Vue 3 + Vite + TypeScript
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install pinia axios markdown-it tailwindcss
npm install -D @types/markdown-it @tailwindcss/vite
```

**核心配置**：

- **Vite**：开发服务器端口 5173，代理 `/api` 到后端 8000
- **Tailwind CSS v4**：CSS-first 配置，通过 `@import "tailwindcss"` 和 `@variant dark` 实现暗色模式
- **TypeScript**：严格模式，路径别名 `@/` 指向 `src/`

#### 4.1.2 后端初始化

```bash
# FastAPI + Python
python -m venv venv
pip install fastapi uvicorn pydantic-settings httpx aiofiles
```

**核心配置**：

- **pydantic-settings**：从 `.env` 文件读取 API Keys（`DEEPSEEK_API_KEY`、`AMAP_API_KEY`）
- **CORS**：允许 `localhost:5173` 跨域访问
- **SQLite**：自动创建 `db/travelmate.db` + 建表

#### 4.1.3 统一 API 客户端

```typescript
// frontend/src/api/client.ts
import axios from 'axios'
import { getDeviceId } from '@/utils/device'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 60000,  // 行程生成可能需要较长时间
})

// 请求拦截器：自动附加设备 ID
api.interceptors.request.use(config => {
  config.headers['X-Device-ID'] = getDeviceId()
  return config
})
```

#### 4.1.4 设备 ID 管理

无需登录注册，使用 `localStorage` 存储 UUID 作为设备标识：

```typescript
export function getDeviceId(): string {
  let id = localStorage.getItem('travelmate_device_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('travelmate_device_id', id)
  }
  return id
}
```

### 4.2 阶段一：前端对话界面基础

#### 4.2.1 组件架构

```
ChatContainer.vue（主布局）
├── SessionSidebar.vue（左侧会话栏）
├── 消息区
│   ├── WelcomePage.vue（空状态欢迎页）
│   ├── MessageBubble.vue × N（消息气泡）
│   │   ├── 文本消息（Markdown 渲染）
│   │   ├── 行程卡片 → TripCard.vue
│   │   ├── 天气消息
│   │   └── 知识消息
│   └── 加载动画（三个跳动点）
├── ChatInput.vue（输入区）
│   └── StyleSelector.vue（风格选择器，条件显示）
└── PreferencePanel.vue（偏好设置抽屉）
```

#### 4.2.2 状态管理（Pinia Store）

```typescript
// stores/chat.ts
export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const sessionId = ref('default')
  const sessions = ref<Session[]>([])

  async function sendMessage(content: string, appendUserMsg = true,
                             existingUserMsgId?: string, tripStyle?: string) {
    // 1. 立即在 UI 中插入用户消息（乐观更新）
    // 2. POST /chat { message, device_id, session_id, trip_style }
    // 3. 根据 intent 映射 message_type
    // 4. 插入 assistant 消息（含 metadata.trip_plan）
  }

  async function switchSession(id: string) {
    // 切换 session_id → GET /sessions/{id}/messages → 重新加载消息列表
  }

  return { messages, isLoading, sessionId, sessions, sendMessage, switchSession, ... }
})
```

#### 4.2.3 核心组件

**MessageBubble.vue**：支持 Markdown 渲染、右键菜单（复制/删除/重新生成）、自动调研标签。

**TripCard.vue**：结构化行程卡片，含标签页导航（行程总览 / Day1 / Day2...）、活动卡片时间轴、餐饮/交通/住宿区块、预算可视化、风格标签 + "换种风格"按钮。

**ChatInput.vue**：大圆角输入框 + 动态 placeholder + 聚焦光环，检测旅行关键词后显示 StyleSelector。

#### 4.2.4 核心代码示例：消息状态管理

```typescript
// frontend/src/stores/chat.ts（核心函数）
export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const sessionId = ref<string>('default')
  const sessions = ref<Session[]>([])

  async function sendMessage(content: string, appendUserMsg = true,
                             existingUserMsgId?: string, tripStyle?: string) {
    const userMsgId = existingUserMsgId ?? crypto.randomUUID()
    // 乐观更新：立即显示用户消息
    if (appendUserMsg) {
      addMessage({ id: userMsgId, role: 'user', content, timestamp: Date.now(), type: 'text' })
    }

    isLoading.value = true
    try {
      const payload: Record<string, any> = {
        message: content, device_id: getDeviceId(), session_id: sessionId.value,
      }
      if (tripStyle) payload.trip_style = tripStyle

      const res = await api.post('/chat', payload)
      addMessage({
        id: crypto.randomUUID(), role: 'assistant', content: res.data.reply,
        timestamp: Date.now(), type: res.data.message_type ?? 'text',
        metadata: res.data.metadata,
      })
      loadSessions()  // 刷新会话列表（触发自动命名更新）
    } catch (err: any) {
      // 错误类型区分：network / timeout / server
      const isNetwork = !err.response || err?.code === 'ERR_NETWORK'
      const isTimeout = err?.code === 'ECONNABORTED'
      markFailed(userMsgId, isNetwork ? 'network' : isTimeout ? 'timeout' : 'server')
    } finally {
      isLoading.value = false
    }
  }

  async function switchSession(id: string) {
    if (id === sessionId.value) return
    sessionId.value = id
    isLoading.value = true
    try {
      const res = await api.get(`/sessions/${id}/messages`, { params: { device_id: getDeviceId() } })
      // 关键：intent → type 映射，TRIP_PLAN → 'card'
      messages.value = res.data.messages.map((m: any) => ({
        id: crypto.randomUUID(), role: m.role, content: m.content,
        timestamp: new Date(m.created_at).getTime(),
        type: m.intent === 'TRIP_PLAN' ? 'card' : 'text',
        metadata: m.metadata ?? undefined,
      }))
    } catch { messages.value = []; addSystemMessage('加载失败') }
    finally { isLoading.value = false }
  }

  return { messages, isLoading, sessionId, sessions, sendMessage, switchSession, ... }
})
```

#### 4.2.5 核心代码示例：会话管理 API

```python
# backend/app/api/sessions.py
@router.get("")
async def list_sessions(device_id: str):
    conn = get_db()
    rows = conn.execute(
        """SELECT s.session_id, s.title, s.created_at, s.updated_at,
                  (SELECT COUNT(*) FROM conversations c
                   WHERE c.device_id = s.device_id AND c.session_id = s.session_id
                   AND c.role != 'system') AS message_count
           FROM sessions s WHERE s.device_id = ?
           ORDER BY s.updated_at DESC""", (device_id,),
    ).fetchall()
    conn.close()
    return {"sessions": [dict(r) for r in rows], "total": len(rows)}

@router.put("/{session_id}/rename")
async def rename_session(session_id: str, device_id: str, req: RenameSessionRequest):
    conn = get_db()
    conn.execute("UPDATE sessions SET title = ? WHERE session_id = ? AND device_id = ?",
                 (req.title, session_id, device_id))
    conn.commit(); conn.close()
    return {"status": "ok", "title": req.title}
```

### 4.4 测试预期与结果

| 测试项 | 操作 | 预期结果 | 实际结果 |
|--------|------|----------|----------|
| 发送消息 | 输入"你好"按回车 | 用户消息出现，加载动画显示，AI 回复出现 | ✅ |
| 会话列表 | 查看左侧栏 | 显示所有会话，按时间倒序 | ✅ |
| 新建会话 | 点击 + 按钮 | 创建新会话，消息列表清空 | ✅ |
| 切换会话 | 点击另一会话 | 加载该会话历史消息，TripCard 正确渲染 | ✅ |
| 删除会话 | 点击删除按钮 | 会话从列表移除，自动切换到其他会话 | ✅ |
| 重命名 | 双击标题→输入新名→回车 | 标题更新 | ✅ |
| 自动命名 | 发送第一条消息 | 会话标题变为消息内容前 15 字 | ✅ |
| 行程命名 | 生成杭州3日游 | 会话标题变为"杭州·3日游" | ✅ |
| TripCard 刷新保持 | 生成行程后刷新页面 | 结构化卡片正常显示，不退化为纯文本 | ✅ |
| 错误处理 | 后端未启动时发消息 | 消息标红 + "网络错误"标签 + 重试按钮 | ✅ |

### 4.3 阶段二：后端 API 网关与基础服务

#### 4.3.1 模块化目录结构

```
backend/app/
├── main.py          # FastAPI 入口 + 路由注册
├── config.py        # pydantic-settings
├── api/             # API 路由层（请求验证 → 调用服务 → 返回响应）
├── services/        # 业务逻辑层（核心处理逻辑）
├── models/          # 数据模型（Pydantic + SQLite）
├── tools/           # 工具注册中心
└── utils/           # 工具函数（安全检查、Prompt 模板）
```

**分层原则**：`api/` 只做请求验证和响应格式化，`services/` 承载所有业务逻辑，`models/` 定义数据结构，`utils/` 提供无状态工具函数。

#### 4.3.2 核心 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 核心对话端点 |
| GET | `/sessions` | 获取会话列表 |
| POST | `/sessions` | 创建新会话 |
| DELETE | `/sessions/{id}` | 删除会话 |
| PUT | `/sessions/{id}/rename` | 重命名会话 |
| GET | `/sessions/{id}/messages` | 获取会话消息历史 |
| GET/DELETE | `/memory/{device_id}/preferences` | 偏好管理 |
| GET | `/weather/current` | 首页天气 |
| POST | `/knowledge/auto-expand` | 知识库自动调研 |
| POST | `/knowledge/auto-expand-batch` | 知识库批量扩充（SSE） |
| GET | `/knowledge/has-local` | 检查本地知识 |
| GET | `/proactive/greet` | 个性化开场问候 |
| GET | `/startup-ts` | 后端启动时间戳 |
| WS | `/ws/{device_id}` | WebSocket 主动推送 |

#### 4.3.3 数据库增量迁移

SQLite 采用 `ALTER TABLE ... ADD COLUMN` + `try/except` 实现增量迁移，无需版本号管理：

```python
# database.py 中建表后自动迁移
try:
    conn.execute("ALTER TABLE conversations ADD COLUMN metadata TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass  # 列已存在
```

---

## 五、核心智能层：意图识别与记忆系统（阶段3-4）

### 5.1 三级意图识别管道

#### 5.1.1 第一层：正则快速匹配

预定义模式匹配常见短语，响应时间 <10ms，零 API 调用成本：

```python
# regex_matcher.py 中的匹配规则
_patterns = {
    r"^(你好|嗨|哈喽|嘿)": ("CHAT", "你好！我是 AI 智游伴，有什么可以帮你的吗？"),
    r"^(再见|拜拜|回见)": ("CHAT", "再见！祝你旅途愉快～"),
    r"^(谢谢|感谢)": ("CHAT", "不客气！有旅行问题随时问我～"),
    r"^(好的|可以|没问题)": ("CHAT", "好的，有需要随时告诉我～"),
}
```

**设计原则**：50 字限制（避免正则在长消息上浪费时间），命中即返回，未命中进入 AI 层。

#### 5.1.2 第二层：AI 意图识别

注入最近 6 条对话历史 + 用户偏好，让 LLM 结合上下文判断意图：

```
系统 Prompt 要求 LLM 输出严格 JSON：
{
  "intent": "WEATHER",
  "sub_intent": "weather_forecast",
  "confidence": 0.95,
  "reasoning": "用户在上一轮询问了杭州天气，本轮提到哈尔滨，应延续天气意图",
  "extracted_data": {"city": "哈尔滨"}
}
```

**关键设计**：
- **上下文延续优先级**：如果上一轮助手在询问某个意图的补充信息（如"请问去几天？"），用户回复应延续该意图
- **个人信息拦截**：检测到用户询问 AI 的名字/年龄等个人信息时，直接走 CHAT 意图，不存入偏好
- **纠正意图检测**：用户说"不对""错了"等纠正语句时，触发知识库纠正闭环

#### 5.1.3 第三层：安全检查

```python
# safety.py 三级安全分类
SAFETY_RULES = {
    "BLOCK": {  # 直接拦截
        "keywords": ["怎么偷", "翻越围栏", "制作炸弹"],
        "reply": "抱歉，我无法处理这类请求。"
    },
    "WARN": {  # 附加警告
        "keywords": ["一个人去", "深夜出行", "无人区"],
        "warning": "提示：该场景存在安全风险，请注意人身安全。"
    },
    "URGENT": {  # 紧急情况
        "keywords": ["高原反应", "中暑", "溺水", "骨折"],
        "warning": "请立即拨打 120 急救电话或前往最近医院！"
    }
}
```

**输出安全过滤**：AI 回复经过二次过滤，确保不包含鼓励危险行为的内容。

### 5.1.4 核心代码示例：安全检查

```python
# backend/app/utils/safety.py
BLOCK_KEYWORDS = ["怎么偷", "怎么骗", "翻越围栏", "闯红灯", "偷窃", "破坏文物", ...]
WARN_KEYWORDS = [
    ("独自旅行", "独自旅行请注意安全，建议告知家人朋友行程。"),
    ("夜路", "夜间出行建议使用正规交通工具，避免偏僻路段。"),
    ("无人区", "进入无人区风险较高，建议结伴同行并提前报备。"),
    ...
]
URGENT_KEYWORDS = [
    ("高原反应", "请立即停止剧烈活动，原地休息，吸氧。严重时拨打120。"),
    ("中暑", "请立即转移到阴凉处，补充淡盐水。严重时拨打120。"),
    ("溺水", "请立即呼救并拨打110/120。切勿盲目下水施救。"),
    ...
]

def input_safety_check(text: str) -> dict:
    text_lower = text.lower()
    for keyword in BLOCK_KEYWORDS:
        if keyword in text_lower:
            return {"passed": False, "level": "BLOCK", "reason": f"包含违禁内容：{keyword}"}
    for keyword, msg in URGENT_KEYWORDS:
        if keyword in text_lower:
            return {"passed": True, "level": "URGENT", "warning": msg}
    for keyword, msg in WARN_KEYWORDS:
        if keyword in text_lower:
            return {"passed": True, "level": "WARN", "warning": msg}
    return {"passed": True, "level": "SAFE"}

# 请求频率限制：每设备每分钟 30 次
_rate_records: dict[str, list[float]] = defaultdict(list)
def check_rate_limit(device_id: str, max_requests: int = 30, window: int = 60) -> bool:
    now = time.time()
    records = _rate_records[device_id]
    _rate_records[device_id] = [t for t in records if now - t < window]
    if len(_rate_records[device_id]) >= max_requests:
        return False
    _rate_records[device_id].append(now)
    return True
```

### 5.1.5 测试预期与结果

| 测试场景 | 输入 | 安全等级 | 预期行为 | 实际结果 |
|----------|------|----------|----------|----------|
| 正常对话 | "我想去杭州" | SAFE | 正常处理 | ✅ |
| 违禁内容 | "怎么偷门票" | BLOCK | 拦截，返回拒绝回复 | ✅ |
| 高风险场景 | "一个人去无人区" | WARN | 正常回复+安全提醒前缀 | ✅ |
| 紧急情况 | "我高原反应了" | URGENT | 回复+急救建议+120 提醒 | ✅ |
| 频率限制 | 1分钟内发30+条 | — | 返回"请求太频繁" | ✅ |
| 输出安全 | AI 回复含"不用担心安全" | 不安全 | 替换为兜底回复 | ✅ |

### 5.2 Hermes 记忆系统

#### 5.2.1 双引擎架构

```
用户偏好
  ├→ SQLite（结构化存储）
  │   ├── 精确查询：SELECT * WHERE category = '饮食'
  │   ├── 统计分析：按 category 分组计数
  │   └── 置信度追踪：每次确认 +0.1
  │
  └→ ChromaDB（向量存储）
      ├── 语义搜索：用户说"我不吃辣" → 检索相关偏好
      ├── 余弦距离：cosine similarity
      └── 上下文注入：查询结果拼入 LLM Prompt
```

#### 5.2.2 核心操作

| 操作 | 函数 | 说明 |
|------|------|------|
| 保存偏好 | `save_memory(device_id, category, key, value)` | 双写 SQLite + ChromaDB |
| 语义搜索 | `query_memory(device_id, query)` | ChromaDB 向量搜索 |
| 获取全部 | `get_all_preferences(device_id)` | SQLite 查询所有偏好 |
| 更新偏好 | `update_memory(device_id, category, key, value)` | 置信度 +0.1 |
| 删除偏好 | `forget_memory(device_id, category, key)` | 双端删除 |

#### 5.2.3 上下文注入

意图识别和行程生成时，自动查询用户偏好并注入 Prompt：

```
用户历史偏好：
- 饮食/素食: true
- 饮食/不吃辣: true
- 预算/日均: 500
- 出行/交通偏好: 高铁优先
```

#### 5.2.4 核心代码示例：双引擎记忆系统

```python
# backend/app/services/memory_service.py
import chromadb
from app.models.database import get_db

# ChromaDB 初始化：余弦相似度向量库
_chroma_client = chromadb.PersistentClient(path="db/chroma_memory")
_memory_collection = _chroma_client.get_or_create_collection(
    name="user_preferences", metadata={"hnsw:space": "cosine"},
)

def save_memory(device_id: str, category: str, key: str, value: str) -> bool:
    """写入偏好（双写：SQLite + ChromaDB）"""
    try:
        # 1. SQLite 写入/更新（置信度递增）
        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM user_preferences WHERE device_id=? AND category=? AND key=?",
            (device_id, category, key)).fetchone()
        if existing:
            conn.execute(
                "UPDATE user_preferences SET value=?, confidence=MIN(confidence+0.1,1.0) "
                "WHERE device_id=? AND category=? AND key=?",
                (value, device_id, category, key))
        else:
            conn.execute(
                "INSERT INTO user_preferences (device_id,category,key,value) VALUES (?,?,?,?)",
                (device_id, category, key, value))
        conn.commit(); conn.close()

        # 2. ChromaDB 向量化写入
        _memory_collection.upsert(
            ids=[f"{device_id}_{category}_{key}"],
            documents=[f"用户偏好：{category}-{key}：{value}"],
            metadatas=[{"device_id": device_id, "category": category,
                        "key": key, "value": value}])
        return True
    except Exception:
        return False

def query_memory(device_id: str, query_text: str, top_k: int = 5) -> list[dict]:
    """语义检索偏好（ChromaDB 向量搜索）"""
    try:
        results = _memory_collection.query(
            query_texts=[query_text], n_results=top_k,
            where={"device_id": device_id})
        return [{"category": m["category"], "key": m["key"], "value": m["value"]}
                for m in results["metadatas"][0]]
    except Exception:
        return _fallback_query(device_id, query_text, top_k)  # SQLite LIKE 兜底
```

#### 5.2.5 测试预期与结果

| 测试场景 | 操作 | 预期结果 | 实际结果 |
|----------|------|----------|----------|
| 保存偏好 | "我不吃辣" → save_memory | SQLite 写入 + ChromaDB 向量化 | ✅ |
| 更新偏好 | 重复保存同 key | 置信度 +0.1（0.8→0.9→1.0 封顶） | ✅ |
| 精确查询 | get_all_preferences("dev1") | 返回所有偏好列表 | ✅ |
| 语义搜索 | query_memory("dev1", "饮食相关") | 返回饮食类偏好 | ✅ |
| ChromaDB 宕机 | 注入异常 | 自动回退到 SQLite LIKE 查询 | ✅ |
| 删除偏好 | forget_memory("dev1", "饮食") | SQLite + ChromaDB 双删 | ✅ |
| 上下文注入 | 行程生成时查偏好 | Prompt 中包含饮食/预算偏好 | ✅ |

---

## 六、外部集成与知识服务（阶段5-7）

### 6.1 外部 API 集成——地图与天气

#### 6.1.1 高德地图服务

| 函数 | 说明 | API |
|------|------|-----|
| `search_poi(keyword, city)` | POI 搜索（景点/酒店/餐厅） | 高德 POI 搜索 |
| `geocode(address)` | 地址 → 经纬度 | 高德地理编码 |
| `reverse_geocode(location)` | 经纬度 → 城市名 | 高德逆地理编码 |
| `get_nearby_food(lng, lat)` | 周边餐厅搜索 | 高德 POI 周边 |

#### 6.1.2 天气服务

```python
def get_weather_forecast(city: str) -> dict:
    """查询城市天气预报，返回当前 + 3 天预报"""
    # 高德天气 API
    # 返回: {days: [{day_weather, night_weather, day_temp, night_temp, day_wind}]}
```

#### 6.1.3 首页天气定位（三层回退）

```
① 用户偏好中设置了"常住城市" → 直接使用（最准确，零延迟）
  ↓ 否
② 浏览器 Geolocation API → 获取经纬度 → 逆地理编码 → 城市名
  ↓ 否/用户拒绝
③ IP 定位（ip-api.com 免费服务）→ 城市级精度
```

### 6.1.4 核心代码示例：天气服务

```python
# backend/app/services/weather_service.py
def get_weather_forecast(city: str) -> dict[str, Any]:
    """获取指定城市的未来天气预报（含缓存）"""
    cache_key = f"weather:forecast:{city.strip().lower()}"
    cached = get_cached_json(cache_key)
    if cached is not None:
        return cached  # 缓存命中

    # 高德天气 API
    geocode = geocode_address(city, city=city)
    city_code = geocode.get("adcode") if geocode else city
    payload = _request_amap_weather("/weather/weatherInfo",
                                    {"city": city_code, "extensions": "all"})
    forecasts = payload.get("forecasts", [])
    days = [{"date": c.get("date"), "day_weather": c.get("dayweather"),
             "night_weather": c.get("nightweather"),
             "day_temp": c.get("daytemp"), "night_temp": c.get("nighttemp"),
             "day_wind": c.get("daywind")} for c in forecasts[0].get("casts", [])]
    result = {"city": city, "report_time": forecasts[0].get("reporttime"), "days": days}
    set_cached_json(cache_key, result, expire_seconds=REDIS_WEATHER_TTL_SECONDS)
    return result
```

### 6.2 行程规划服务

#### 6.2.1 生成流程

```
generate_trip_plan(device_id, destination, days, style)
  ├── 1. 获取用户偏好（get_all_preferences）
  ├── 2. 搜索目的地 POI（search_poi × 3 类型：景点/酒店/餐厅）
  ├── 3. 查询目的地天气（get_weather_forecast）
  ├── 4. 拼装 Prompt（含风格指令 STYLE_INSTRUCTIONS）
  ├── 5. 调用 LLM 生成结构化 JSON
  ├── 6. JSON 解析 + 容错处理
  │     ├── Primary: json.loads()
  │     ├── Fallback 1: 正则提取 {...} 片段
  │     └── Fallback 2: 降级为 Markdown 文本
  ├── 7. Pydantic Itinerary 校验（自动补全默认值）
  ├── 8. 存入 SQLite trip_plans 表
  └── 9. 返回 {summary, itinerary_json, destination, days}
```

#### 6.2.2 三种行程风格

| 风格 | 代码 | 标识 | 每日景点数 | 特点 |
|------|------|------|-----------|------|
| 紧凑打卡型 | `compact` | ⚡ | 5-7 个 | 早出晚归，高效打卡 |
| 休闲度假型 | `leisure` | 🌴 | 2-3 个 | 慢节奏享受，留足休息 |
| 深度文化型 | `culture` | 📚 | 3-5 个 | 侧重博物馆、历史遗迹 |

风格通过 `STYLE_INSTRUCTIONS` 字典注入 Prompt，TripCard 上显示当前风格标签 + "换种风格"按钮。

#### 6.2.4 核心代码示例：行程生成

```python
# backend/app/services/trip_service.py（核心函数）
async def generate_trip_plan(device_id: str, destination: str,
                             days: int, style: str = "default") -> dict:
    # 1. 收集数据
    poi_text = _format_poi_text(destination)       # 高德 POI 搜索
    weather_text = _format_weather_text(destination) # 天气预报
    preferences_text = _format_preferences_text(device_id)  # 用户偏好
    style_instructions = STYLE_INSTRUCTIONS.get(style, "")   # 风格指令

    # 2. 组装 Prompt + 调用 LLM
    prompt = TRIP_PLAN_PROMPT.format(
        destination=destination, days=days, poi_text=poi_text,
        weather_text=weather_text, preferences_text=preferences_text,
        style_instructions=style_instructions)
    raw = await call_llm(messages=[{"role":"user", "content": f"规划{destination}{days}天行程"}],
                         system_prompt=prompt, temperature=0.7, max_tokens=3000)

    # 3. JSON 解析（含容错）
    plan_dict = _parse_trip_json(raw, destination)
    # 直接解析 → 正则提取 {...} → 失败抛异常

    # 4. Pydantic 校验
    plan_dict["trip_id"] = f"trip_{uuid.uuid4().hex[:8]}"
    plan_dict["destination"] = destination
    itinerary = Itinerary(**plan_dict)  # 自动补全缺失字段默认值

    # 5. 存储 + 返回
    _save_trip_to_db(device_id, destination, days,
                     json.dumps(itinerary.model_dump(), ensure_ascii=False))
    return {"trip_id": itinerary.trip_id, "destination": destination,
            "days": days, "summary": itinerary.summary,
            "itinerary_json": itinerary.model_dump()}
```

#### 6.2.5 核心代码示例：RAG 知识检索与兜底

```python
# backend/app/services/rag_service.py（核心函数）
async def query_knowledge(question: str, spot_name: str | None = None) -> str:
    # 第一步：指定景点的直接检索
    if spot_name:
        direct_match = retrieve_knowledge(question, spot_name=spot_name, top_k=5)
        if not direct_match:
            from app.services.knowledge_expander import auto_expand, has_local_knowledge
            if not has_local_knowledge(spot_name):
                try:
                    expand_result = await auto_expand(spot_name)  # 自动调研
                    if expand_result.get("status") == "ok":
                        direct_match = retrieve_knowledge(question, spot_name=spot_name, top_k=5)
                        if direct_match:
                            context = "\n\n".join(f"【{r['spot_name']}】{r['text']}" for r in direct_match)
                            answer = await call_llm(system_prompt=f"基于知识回答：\n{context}", ...)
                            return f"🔍 已为你自动调研了「{spot_name}」\n\n{answer}"
                except Exception: pass

    # 第二步：通用语义检索
    retrieved = retrieve_knowledge(question, spot_name=None, top_k=5)

    # 兜底 1：检索为空 → LLM 通用知识 + 诚实标注
    if not retrieved:
        answer = await call_llm(system_prompt="知识库无资料，请基于通用知识回答..."
                                "末尾加'以上基于通用知识整理'", ...)
        return answer

    # 兜底 2：spot_name 明确但无匹配 → 低置信度标记
    if spot_name and not [r for r in retrieved if r["spot_name"] == spot_name]:
        answer = await call_llm(system_prompt="无直接资料，以下为参考内容...", ...)
        return answer

    # 正常：注入 Context → 导游式回答
    prompt = KNOWLEDGE_QA_PROMPT.format(context=context, question=question)
    return await call_llm(system_prompt=prompt, ...)
```

#### 6.2.6 核心代码示例：知识库自动调研

```python
# backend/app/services/knowledge_expander.py
KNOWLEDGE_GEN_PROMPT = """你是「AI智游伴」的知识编辑。为景点「{spot_name}」生成旅游知识文档。
文档结构：简介 → 历史文化 → 主要看点 → 游玩建议 → 实用信息
要求：800-1500字，语言生动，Markdown格式。"""

async def auto_expand(spot_name: str) -> dict:
    """自动调研管线：LLM 生成知识 → 保存 → 向量化"""
    content = await _generate_knowledge(spot_name)  # LLM 直接生成
    if not content or len(content.strip()) < 50:
        return {"status": "generate_failed"}
    _save_knowledge_file(spot_name, content)          # 保存 .md
    chunk_count = _vectorize_single(spot_name, content) # 向量化入库
    return {"status": "ok", "spot_name": spot_name, "chunk_count": chunk_count}

async def correct_knowledge(correction_message: str) -> dict:
    """用户反馈纠正闭环"""
    # 1. LLM 提取纠正信息 → JSON {spot_name, original_fact, corrected_fact}
    # 2. 查找对应 .md 文件
    # 3. LLM 修改文档中的错误段落
    # 4. 保存 + 重新向量化
```

### 6.3 RAG 景点知识服务

#### 6.3.1 知识库加载

```
data/knowledge/*.md（每个景点一个 Markdown 文件）
  ↓ 启动时扫描
  ↓ 按 \n\n 分块
  ↓ ChromaDB ONNX 向量化
  ↓ spot_knowledge 集合（cosine 相似度）
```

#### 6.3.2 知识检索与回答

```
query_knowledge(question, spot_name)
  ├── ChromaDB 语义检索 top_k=5
  │
  ├── 【兜底 1】检索为空 → LLM 通用知识回答 + 诚实标注
  │     "以上信息基于通用知识整理，如需更详尽的当地攻略..."
  │
  ├── 【兜底 2】检索到不相关内容（跨目的地误匹配）
  │     → 低置信度标记 → LLM 可以忽略 Context
  │
  ├── 【兜底 3】本地无知识 + 自动调研
  │     DuckDuckGo 搜索 → LLM 策展 → 入库 → 重检
  │     返回 "🔍 已为你自动调研了「景点名」"
  │
  └── 【正常】有匹配知识 → 注入 Context → LLM 导游式回答
```

#### 6.3.3 知识库自动调研管线

```
触发条件：RAG 检索为空 + has_local_knowledge() = false

auto_expand(spot_name):
  ├── 1. DuckDuckGo 搜索 "{spot_name} 旅游攻略 景点介绍"
  ├── 2. LLM 策展（CURATION_PROMPT）
  │     分为：简介、历史文化、主要看点、游玩建议、实用信息
  │     800-1500 字，语言生动，像导游在向朋友介绍
  ├── 3. 保存到 data/knowledge/{spot_name}.md
  └── 4. 向量化入库 ChromaDB
```

**端到端示例**：

```
用户：平遥古城有什么历史？
  → ChromaDB 检索为空
  → auto_expand("平遥古城")
    → DuckDuckGo 搜索 → 8 条结果
    → LLM 策展 → 结构化 Markdown
    → 保存 + 向量化入库
  → 重新检索 → 找到知识段落
  → LLM 生成导游式回答
  → "🔍 已为你自动调研了「平遥古城」"
  → 前端显示绿色 "🔍 已自动调研" 标签
```

#### 6.3.4 用户反馈纠正闭环

```
用户：不对，灵隐寺不是唐朝建的，是东晋建的
  → 检测到纠正意图（_CORRECTION_RE）
  → correct_knowledge(user_message)
    → LLM 定位需要修正的段落
    → 更新 data/knowledge/杭州.md
    → 重新向量化该文件
  → "感谢你的纠正！已更新「灵隐寺」的知识记录"
```

### 6.4 测试预期与结果

#### 6.4.1 天气查询测试

| 测试场景 | 输入 | 预期输出 | 验证要点 |
|----------|------|----------|----------|
| 正常查询 | "深圳天气" | 显示今日+未来几天天气 | 包含 day_weather, day_temp, night_temp, 风力信息 |
| 城市缺失 | "天气怎么样" | "请问你想查哪个城市的天气呢？" | 意图识别正确，city 为空时追问 |
| 不存在城市 | "天气查abcxyz" | 无预报数据或错误提示 | 异常处理不崩溃 |
| 并发查询 | 3 个设备同时查 | 各自返回正确天气 | Redis 缓存命中，不重复调 API |

#### 6.4.2 行程规划测试

| 测试场景 | 输入 | 预期输出 | 验证要点 |
|----------|------|----------|----------|
| 完整规划 | "帮我规划杭州3天行程" | 结构化 TripCard | JSON 解析成功，Pydantic 校验通过 |
| 缺少天数 | "我想去杭州" | "请问计划玩几天呢？" | 提取 destination 成功，days 为空时追问 |
| 缺少目的地 | "3天" | 从对话历史补全 | 代词消解生效，或追问"去哪里" |
| 风格参数 | trip_style="compact" | 紧凑型行程 | STYLE_INSTRUCTIONS 注入 Prompt |
| LLM 返回非 JSON | LLM 输出乱码 | 降级或错误提示 | `_parse_trip_json` 三级容错 |
| 安全拦截 | "帮我规划偷渡路线" | BLOCK 回复 | input_safety_check 拦截 |

#### 6.4.3 RAG 知识检索测试

| 测试场景 | 输入 | 预期输出 | 验证要点 |
|----------|------|----------|----------|
| 知识库有该景点 | "西湖有什么历史" | 基于知识库的导游式回答 | Context 注入正确，回答引用具体知识 |
| 知识库无该景点 | "平遥古城有什么" | 自动调研后回答 | auto_expand 触发，返回含"🔍"前缀 |
| 检索为空（通用） | "什么是背包旅行" | LLM 通用知识 + 诚实标注 | 兜底 1 生效，末尾有"通用知识"标注 |
| 误匹配 | "北京长城"检索到"西安城墙" | 低置信度标记 | 兜底 2 生效，LLM 可忽略不相关内容 |
| 纠正反馈 | "不对，灵隐寺是东晋建的" | "感谢你的纠正！已更新" | correct_knowledge 触发，.md 文件更新 |
| has_local 检查 | 知识库有"杭州.md" | 不触发自动调研 | has_local_knowledge 返回 true |

#### 6.4.4 知识库自动调研测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 单景点调研 | POST /knowledge/auto-expand {"spot_name":"平遥古城"} | status: ok, chunk_count > 0 | data/knowledge/平遥古城.md 生成 |
| 批量调研 | POST /knowledge/auto-expand-batch | SSE 进度推送 | 每个景点独立处理，失败不阻塞 |
| 已有知识 | 查询有本地知识的景点 | 不触发调研 | has_local_knowledge 为 true |
| LLM 生成失败 | 模拟 LLM 返回空 | status: generate_failed | len(content) < 50 检查 |
| 搜索无结果 | DuckDuckGo 返回 0 条 | 降级为纯 LLM 生成 | 不崩溃，正常返回 |

#### 6.4.5 会话自动命名测试

| 测试场景 | 触发条件 | 预期标题 | 验证要点 |
|----------|----------|----------|----------|
| 行程规划 | intent=TRIP_PLAN + trip_plan 存在 | "杭州·3日游" | 以目的地+天数命名 |
| 首条消息 | 标题为"新会话" | 截取前 15 字 | _generate_title 生效 |
| 手动重命名 | 用户已改标题 | 不覆盖 | current_title != "新会话" |
| 无目的地行程 | destination 为空 | 保留原标题 | 不错误覆盖 |

---

## 七、主动服务与安全体系（阶段8-10）

### 7.1 主动服务机制

#### 7.1.1 WebSocket 实时推送

```python
# 连接管理
active_connections: dict[str, WebSocket] = {}

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    active_connections[device_id] = websocket
    # 保持连接，等待主动推送
```

#### 7.1.2 个性化开场问候

**触发时机**：
| 场景 | 条件 | 行为 |
|------|------|------|
| 新用户 | 无偏好、无历史消息 | 欢迎语 + 功能介绍 |
| 回访用户 | 有偏好或历史行程 | 问候 + 天气 + 回忆偏好 |
| 每日首次打开 | 距上次问候超过 6 小时 | 重新生成当日问候 |

**问候内容构成**：时间问候 + 所在地天气 + 回忆偏好/行程 + 开放式邀请

**防重复机制**：`localStorage` 记录最近问候时间戳，6 小时内不重复。

#### 7.1.3 天气提醒

APScheduler 定时任务：
- 每日 20:00 检查用户所在地天气
- 检测到次日降雨 → WebSocket 推送提醒
- 用户到达景点 → 触发到达欢迎语

### 7.2 前端-后端业务串联

#### 7.2.1 消息流程

```
用户输入 → handleSend(text, tripStyle?)
  → store.sendMessage(text, true, undefined, tripStyle)
    → [乐观更新] 立即显示用户消息
    → POST /chat { message, device_id, session_id, trip_style }
    → [响应处理] 根据 intent 映射 message_type
    → 插入 assistant 消息（含完整 metadata）
    → [TripCard 检测] intent=TRIP_PLAN && metadata.trip_plan 存在
    → 渲染结构化行程卡片
```

#### 7.2.2 会话切换流程

```
switchSession(sessionId)
  → GET /sessions/{sessionId}/messages
  → [消息映射] intent → type：
      TRIP_PLAN → 'card'
      WEATHER → 'weather'
      KNOWLEDGE → 'knowledge'
      其他 → 'text'
  → [TripCard 恢复] 检查 msg.type === 'card' && msg.role === 'assistant' && !!msg.metadata?.trip_plan
  → 刷新消息列表
```

#### 7.2.3 行程风格切换

```
TripCard 点击"换种风格"
  → ChatContainer.handleSwitchStyle(msg)
    → 找到对应的 user 消息
    → 显示 StyleSelector（带取消按钮）
  → 用户选择新风格
    → handleStyleSwitchSelect(style)
      → 发送原消息 + 新风格参数
      → 生成新行程卡片
```

### 7.3 安全系统

#### 7.3.1 输入安全

- **关键词拦截**：非法活动、危险行为
- **场景警告**：独行、夜行、无人区
- **紧急识别**：高原反应、中暑、溺水
- **限流保护**：每设备每分钟 30 次请求

#### 7.3.2 输出安全

- LLM 输出经 `filter_llm_output()` 过滤
- 检测到不安全内容时替换为兜底回复
- 安全等级附加在 metadata 中，前端可展示警告

### 7.4 核心代码示例

#### 7.4.1 WebSocket 连接管理 + 消息推送

```python
# backend/app/services/proactive_service.py（连接池 + 推送）
_connections: dict[str, WebSocket] = {}

def register_ws(device_id: str, ws: WebSocket) -> None:
    _connections[device_id] = ws

def unregister_ws(device_id: str) -> None:
    _connections.pop(device_id, None)

async def push_message(device_id: str, content: str, msg_type: str = "proactive") -> bool:
    ws = _connections.get(device_id)
    if ws is None:
        return False
    payload = json.dumps({
        "type": msg_type, "content": content,
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)
    await ws.send_text(payload)
    return True
```

```python
# backend/app/main.py（WebSocket 端点）
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
```

#### 7.4.2 个性化开场问候生成

```python
# backend/app/services/proactive_service.py（问候生成）
GREETING_PROMPT = """你是「AI智游伴」的个性化问候生成器。
时间：{time_of_day}  天气：{weather}
新用户：{is_new_user}  偏好：{preferences}  行程：{recent_trips}

新用户：时间问候 + 天气 + 功能介绍 + 引导问题
回访用户：时间问候 + 天气 + 提及偏好/未完成行程 + 开放邀请
要求：2-4句，温暖自然，不要客服腔。"""

async def generate_greeting(device_id: str) -> dict[str, Any]:
    prefs = get_all_preferences(device_id)
    recent_trips = query_trip_plans(device_id, limit=2)
    is_new = (len(prefs) == 0 and len(recent_trips) == 0)
    # 优先用用户 home_city 天气，否则用深圳默认
    weather_text = _get_weather_for_greeting(prefs)
    prompt = GREETING_PROMPT.format(
        time_of_day=_time_greeting(), weather=weather_text,
        is_new_user=str(is_new), preferences=_fmt_prefs(prefs),
        recent_trips=_fmt_trips(recent_trips))
    greeting = await call_llm(messages=[...], system_prompt=prompt, temperature=0.8, max_tokens=300)
    return {"greeting": greeting, "is_new_user": is_new}
```

#### 7.4.3 天气定时提醒 + 到达问候

```python
# backend/app/services/proactive_service.py（定时任务）
async def _weather_check_job(device_id: str, city: str) -> None:
    data = get_weather_forecast(city)
    today = data.get("days", [{}])[0]
    rain_keywords = ["雨", "雷", "阵雨", "暴雨"]
    has_rain = any(kw in today.get("day_weather", "") or kw in today.get("night_weather", "")
                   for kw in rain_keywords)
    if not has_rain:
        return
    prefs = get_all_preferences(device_id)
    prompt = f"明天{city}有雨，请用1-2句话提醒用户注意天气。"
    reply = await call_llm(messages=[...], system_prompt=prompt, temperature=0.7, max_tokens=200)
    await push_message(device_id, reply, msg_type="weather_alert")

def set_weather_reminder(device_id, city, hour=20, minute=0) -> str:
    job_id = f"weather_{device_id}_{city}"
    _scheduler.add_job(_weather_check_job, trigger=CronTrigger(hour=hour, minute=minute),
                       args=[device_id, city], id=job_id, replace_existing=True)
    return job_id

async def send_arrival_greeting(device_id, spot_name, city="") -> str:
    prompt = f"用户刚到达{city}的「{spot_name}」，请热情打招呼并介绍一个亮点。"
    greeting = await call_llm(messages=[...], system_prompt=prompt, temperature=0.8, max_tokens=150)
    await push_message(device_id, greeting, msg_type="arrival_greeting")
    return greeting
```

#### 7.4.4 三级安全检查 + 频率限制

```python
# backend/app/utils/safety.py（输入安全三级检查）
def input_safety_check(text: str) -> dict:
    text_lower = text.lower()
    # BLOCK：违禁内容 → 直接拦截
    for keyword in BLOCK_KEYWORDS:
        if keyword in text_lower:
            return {"passed": False, "level": "BLOCK", "reason": f"包含违禁内容：{keyword}"}
    # URGENT：紧急情况 → 回答 + 附带紧急联系方式
    for keyword, msg in URGENT_KEYWORDS:
        if keyword in text_lower:
            return {"passed": True, "level": "URGENT", "warning": msg}
    # WARN：风险提示 → 回答 + 附加安全提醒
    for keyword, msg in WARN_KEYWORDS:
        if keyword in text_lower:
            return {"passed": True, "level": "WARN", "warning": msg}
    return {"passed": True, "level": "SAFE"}
```

```python
# backend/app/utils/safety.py（频率限制 — 滑动窗口）
_rate_records: dict[str, list[float]] = defaultdict(list)

def check_rate_limit(device_id: str, max_requests: int = 30, window: int = 60) -> bool:
    now = time.time()
    _rate_records[device_id] = [t for t in _rate_records[device_id] if now - t < window]
    if len(_rate_records[device_id]) >= max_requests:
        return False  # 超限
    _rate_records[device_id].append(now)
    return True
```

```python
# backend/app/utils/safety.py（输出安全过滤）
DANGEROUS_OUTPUT_PHRASES = [
    "建议你去翻越", "可以尝试逃票", "不用担心安全",
    "爬围栏", "不用买票", "偷偷进去",
]

async def filter_llm_output(raw_text: str) -> str:
    for phrase in DANGEROUS_OUTPUT_PHRASES:
        if phrase in raw_text:
            return "抱歉，我暂时无法回答这个问题。如果你需要旅行方面的帮助，随时可以问我～"
    return raw_text
```

### 7.5 测试预期与结果

#### 7.5.1 WebSocket 连接测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 正常连接 | 前端建立 WS 连接 | 连接成功，_connections 池中注册 | 日志显示"WebSocket 已注册" |
| ping/pong | 发送 "ping" | 返回 `{"type":"pong"}` | 保活机制正常 |
| 断连清理 | 前端关闭连接 | _connections 中自动移除 | WebSocketDisconnect 触发 unregister_ws |
| 推送到在线设备 | push_message(device_A) | 设备 A 收到 JSON 消息 | 含 type, content, timestamp 字段 |
| 推送到离线设备 | push_message(device_B)（未连接） | 返回 False，不崩溃 | 日志警告"设备未连接" |
| 推送异常 | 模拟 ws.send_text 抛异常 | unregister_ws 清理 + 返回 False | 不影响其他连接 |

#### 7.5.2 个性化问候测试

| 测试场景 | 条件 | 预期输出 | 验证要点 |
|----------|------|----------|----------|
| 新用户 | 无偏好 + 无行程 | 欢迎语 + 功能介绍 + 引导问题 | is_new_user=true，不含历史偏好 |
| 回访用户 | 有偏好 + 有行程 | 问候 + 提及偏好/未完成行程 | 自然融入偏好，不生硬列举 |
| 有 home_city | 偏好含 home_city="杭州" | 显示杭州天气 | 天气数据正确获取 |
| 无 home_city | 无位置偏好 | 默认深圳天气 | 兜底城市生效 |
| 防重复 | 6 小时内重复调用 | 返回 "skipped" | greeted 字段已标记 |
| 每日首次 | 距上次问候 >6 小时 | 重新生成问候 | greeted 字段重置 |

#### 7.5.3 天气提醒测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 有雨提醒 | 设置深圳每日 20:00 检查，当天有雨 | 20:00 推送雨天提醒 | push_message 触发，含穿衣建议 |
| 无雨静默 | 当天晴天 | 不推送 | has_rain=False，直接 return |
| 重复设置 | 同一 device_id+city 重复设置 | 覆盖旧 job | replace_existing=True |
| 取消提醒 | DELETE /proactive/weather-check/{job_id} | 任务移除 | scheduler.get_job 返回 None |

#### 7.5.4 安全系统测试

| 测试场景 | 输入 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| BLOCK 拦截 | "怎么偷东西" | passed=False, level=BLOCK | 直接拦截，不进入意图识别 |
| URGENT 紧急 | "我高原反应了" | passed=True, level=URGENT | 附带紧急处理建议 + 120 提示 |
| WARN 警告 | "我要独自旅行" | passed=True, level=WARN | 附带安全提醒，回复正常生成 |
| SAFE 正常 | "帮我规划杭州行程" | passed=True, level=SAFE | 无安全干预 |
| 输出过滤 | LLM 回复含"建议你去翻越" | 替换为兜底回复 | filter_llm_output 生效 |
| 输出正常 | LLM 回复正常内容 | 原文返回 | 无误过滤 |
| 频率限制 | 1 分钟内发 31 条消息 | 第 31 条返回"请求太频繁" | check_rate_limit 生效 |
| 频率恢复 | 等待 61 秒后重发 | 正常处理 | 滑动窗口过期清理 |

---

## 八、增强功能与部署（阶段11-12）

### 8.1 语音交互

#### 8.1.1 语音识别（ASR）

```typescript
// frontend/src/composables/useSpeechRecognition.ts
export function useSpeechRecognition() {
  const isListening = ref(false)
  const transcript = ref('')
  const errorMsg = ref('')
  const isSupported = ref(
    'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
  )

  let recognition: any = null

  function initRecognition() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) return null
    const rec = new SR()
    rec.lang = 'zh-CN'
    rec.continuous = true
    rec.interimResults = true

    rec.onresult = (event: any) => {
      const parts: string[] = []
      for (let i = 0; i < event.results.length; i++) {
        if (event.results[i].isFinal) parts.push(event.results[i][0].transcript)
      }
      if (parts.length > 0) transcript.value = parts.join('')
      // 最后一条结果为 final 时，1.5s 静默后自动停止
      if (event.results[event.results.length - 1]?.isFinal) {
        silenceTimer = setTimeout(() => stop(), 1500)
      }
    }

    rec.onerror = (event: any) => {
      const errMap: Record<string, string> = {
        'no-speech': '未检测到语音', 'audio-capture': '未找到麦克风',
        'not-allowed': '麦克风权限未授权', 'network': '需要网络连接',
      }
      errorMsg.value = errMap[event.error] || `语音错误: ${event.error}`
      isListening.value = false
      recognition = null  // 错误后重建
    }
    return rec
  }

  function start() {
    recognition = recognition || initRecognition()
    transcript.value = ''; errorMsg.value = ''
    recognition?.start(); isListening.value = true
  }

  function stop() {
    recognition?.stop(); isListening.value = false
    // 清理末尾标点
    transcript.value = transcript.value.replace(/[。，！？、；：""''（）\s]+$/g, '').trim()
  }

  return { isListening, transcript, errorMsg, isSupported, start, stop }
}
```

#### 8.1.2 语音播报（TTS）

```typescript
// frontend/src/composables/useSpeechSynthesis.ts
export function useSpeechSynthesis() {
  const isSpeaking = ref(false)
  const isSupported = ref('speechSynthesis' in window)

  function speak(text: string, lang = 'zh-CN') {
    if (!isSupported.value) return
    speechSynthesis.cancel()
    // 去除 Markdown 格式：**粗体** → 粗体，## 标题 → 标题，换行 → 句号
    const cleanText = text
      .replace(/#{1,6}\s/g, '').replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1').replace(/`(.*?)`/g, '$1')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1').replace(/[>|\-|•]/g, '')
      .replace(/\n{2,}/g, '。').replace(/\n/g, '，').trim()

    const utterance = new SpeechSynthesisUtterance(cleanText)
    utterance.lang = lang; utterance.rate = 1.0
    utterance.onend = () => { isSpeaking.value = false }
    utterance.onerror = () => { isSpeaking.value = false }
    isSpeaking.value = true
    speechSynthesis.speak(utterance)
  }

  function stop() { speechSynthesis.cancel(); isSpeaking.value = false }
  return { isSpeaking, isSupported, speak, stop }
}
```

### 8.2 联调优化与测试

#### 8.2.1 性能优化

| 优化项 | 措施 |
|--------|------|
| 前端加载 | 代码分割 + 懒加载（动态 `import()`） |
| 后端响应 | 正则预编译 + 缓存 Prompt 模板 |
| 数据库 | ChromaDB HNSW 索引调优 |
| 网络 | Axios 请求去重 + 响应缓存 |

#### 8.2.2 部署方案

| 方式 | 前端 | 后端 | 适用场景 |
|------|------|------|----------|
| 开发环境 | `npm run dev`（Vite 5173） | `uvicorn`（8000） | 本地开发 |
| 生产环境 | Nginx 静态文件 | Gunicorn + Uvicorn Workers | 服务器部署 |

### 8.3 测试预期与结果

#### 8.3.1 语音识别测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 正常识别 | 点击麦克风 → 说"杭州天气" | transcript 显示"杭州天气" | isFinal 拼接正确 |
| 浏览器不支持 | Firefox（无 Web Speech API） | isSupported=false，按钮隐藏 | 不报错 |
| 麦克风拒绝 | 用户拒绝权限 | errorMsg="麦克风权限未授权" | onerror 捕获 |
| 无语音输入 | 开启后不说话 | 1.5s 后自动停止 | silenceTimer 生效 |
| 静默清理 | 识别完成 | 末尾标点被清理 | 正则清理"。"等 |
| 重新识别 | 停止后再启动 | transcript 清空，重新开始 | recognition 重建 |

#### 8.3.2 语音播报测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 正常播报 | speak("今天天气晴朗") | 语音播放 | utterance.lang='zh-CN' |
| Markdown 清理 | speak("**西湖**很美\n\n推荐") | 播报"西湖很美。推荐" | 格式符号被清除 |
| 打断播报 | speak 中调用 stop() | 停止播放 | speechSynthesis.cancel() |
| 连续播报 | 快速调用 2 次 speak | 只播最新一次 | 先 cancel 再 speak |
| 不支持 | 浏览器无 speechSynthesis | 静默跳过 | isSupported=false |

---

## 九、优化升级方案

> 以下优化基于对项目全部代码的审查（14 个后端服务/工具文件、15 个前端源文件），按优先级分为 P0-P3 四个阶段。

### 9.1 优化总览与优先级

| 优先级 | 模块 | 改造范围 | 预估工作量 |
|--------|------|----------|-----------|
| P0 | TripCard 重设计 | 后端 Prompt + trip_service + chat.py + 前端 TripCard | 中 |
| P0 | KNOWLEDGE 兜底逻辑 | rag_service.py 双层兜底 | 小 |
| P0 | 会话管理 | 后端 sessions API + 前端侧边栏 | 中 |
| P0 | 偏好管理面板 | 后端已有 API + 前端设置页 | 小 |
| P1 | 行程导出 | 后端 export_service + 前端按钮 | 小 |
| P1 | 错误恢复与重试 | 前端 store + MessageBubble | 小 |
| P1 | 消息操作菜单 | 前端 MessageBubble 右键菜单 | 小 |
| P2 | 预算估算器 | 后端 Prompt 增强 | 小 |
| P2 | 旅行准备清单 | 后端 checklist 服务 + 前端展示 | 中 |
| P2 | 聊天界面美化 | 布局重构 + 暖色调 + 暗色模式 | 中 |
| P2 | 首页天气显示 | 后端 IP 定位 + 天气组件 | 小 |
| P2 | 会话启动问候 | 后端 greet 端点 + 前端检测 | 小 |
| P3 | 知识库自动调研 | DuckDuckGo → LLM → 自动入库 | 中 |
| P3 | 行程风格对比 | 后端 style 参数 + 前端选择器 | 中 |

### 9.2 实施顺序（按依赖关系）

```
P0 ─ 核心价值 + 修 Bug ─────────────────────────

  ① 十   KNOWLEDGE 兜底      最快见效，只改 rag_service.py
  ② 一   TripCard 重设计      最大块，后端 Prompt + 前端组件
  ③ 三   偏好管理面板         纯前端，后端 API 已就绪
  ④ 二   会话管理             为后续 UI 打基础

P1 ─ 体验短板 ──────────────────────────────────

  ⑤ 五   错误恢复             store + MessageBubble 小改
  ⑥ 六   消息操作菜单         MessageBubble 右键菜单
  ⑦ 四   行程导出             后端 export_service + 前端按钮

P2 ─ 锦上添花（有依赖链）─────────────────────

  ⑧ 十二  首页天气            三层定位 + 天气查询
  ⑨ 十三  会话启动问候        依赖 ⑧ 的天气数据
  ⑩ 九    整体美化            等侧边栏和天气就位再统一调整
  ⑪ 七    预算估算器          Prompt 微调
  ⑫ 八    旅行准备清单        独立服务

P3 ─ 长期优化 ──────────────────────────────────

  ⑬ 十.6  知识库自动调研      DuckDuckGo → LLM → 入库
  ⑭ 十一  行程风格对比        后端 style + 前端选择器
```

**关键依赖链**：⑧ 首页天气 → ⑨ 会话问候 → ⑩ 整体美化（三者必须按此顺序）

### 9.3 P0：TripCard 行程卡片重设计

#### 9.3.1 改造目标

将 Markdown 文本渲染的行程卡片升级为**多标签结构化交互卡片**。

**数据流改造**：

```
【改造前】
LLM → Markdown 字符串 → reply → TripCard(markdown-it 渲染)

【改造后】
LLM → JSON 字符串 → Pydantic Itinerary 校验 → {
    reply: itinerary.summary (简短概述)
    metadata.trip_plan: itinerary.model_dump() (完整结构化数据)
} → TripCard 多标签结构化卡片
```

#### 9.3.2 TripCard 组件结构

```
TripCard.vue
├── Header（目的地 + 天数标签 + 风格标签 + 换种风格按钮）
├── TabBar（行程总览 / Day 1 / Day 2 / Day 3...）
├── TabContent
│   ├── [行程总览] summary + 预算拆分 + tips
│   └── [Day N] 主题 + 时间轴景点列表 + 餐饮卡片 + 住宿
└── BottomNav（交通 / 美食 / 住宿 汇总弹层）
```

#### 9.3.3 LLM JSON 输出容错

1. **Primary**：直接 `json.loads()`
2. **Fallback 1**：正则提取 `{...}` 片段后重试
3. **Fallback 2**：完全无法解析时降级为旧版 Markdown 渲染

### 9.4 P0：KNOWLEDGE 双层兜底逻辑

**问题**：检索为空时直接返回"暂时没有找到"，即使 LLM 可以回答。

**改造**：

```python
if not retrieved:
    # 兜底 1：知识库为空 → LLM 通用知识回答 + 诚实标注
    answer = await call_llm(system_prompt="基于通用知识回答...")

if spot_name and not matching_chunks:
    # 兜底 2：检索到不相关内容 → 标记低置信度 → LLM 可忽略
    prompt = "知识库无直接资料，以下为参考内容..."
```

**改造成果**：

| 场景 | 改造前 | 改造后 |
|------|--------|--------|
| 知识库中有该景点 | ✅ 正常 | ✅ 不受影响 |
| 知识库无该景点（检索为空） | ❌ "暂时没有找到" | ✅ LLM 通用知识 + 标注 |
| 知识库无该景点（误匹配） | ⚠️ 噪音 Context | ✅ 低置信度标记 |

### 9.5 P0：会话管理系统

#### 9.5.1 后端 API

```
GET    /sessions?device_id=xxx          → 会话列表（标题/消息数/时间）
POST   /sessions                        → 创建新会话
DELETE /sessions/{session_id}           → 删除会话（含消息）
PUT    /sessions/{session_id}/rename    → 重命名会话
GET    /sessions/{session_id}/messages  → 消息历史（含 metadata JSON 解析）
```

#### 9.5.2 前端侧边栏

- **新建会话按钮**（+ 图标）
- **会话列表**：按更新时间倒序，显示标题 + 创建时间（HH:MM）
- **当前会话高亮**：amber 左边框 + 背景
- **操作按钮**：hover 显示重命名（铅笔）和删除（×）按钮
- **双击重命名**：内联输入框 + Enter 确认 + Esc 取消

### 9.6 P0：偏好管理面板

后端 API 已就绪，前端新增右侧抽屉面板：
- 分类展示（饮食/出行/住宿/其他）
- 每条偏好：key → value + 删除按钮
- 手动添加：选择 category → 输入 key/value

### 9.7 P1：错误恢复与重试

- 区分错误类型：NetworkError / ServerError / TimeoutError
- 失败消息标红 + "重新发送"按钮
- 连续失败 3 次后提示"请检查后端是否启动"

### 9.8 P1：聊天消息操作菜单

MessageBubble 右键/长按弹出操作菜单：

| 操作 | 适用消息 | 行为 |
|------|----------|------|
| 复制文本 | 全部 | 复制到剪贴板 |
| 重新生成 | assistant | 重新发送对应 user 消息 |
| 删除 | 全部 | 从列表和数据库中移除 |
| 播报 | assistant（文本） | TTS 朗读 |

### 9.9 P1：行程导出

TripCard 底部新增两个按钮：
- **导出 PDF**：ReportLab 生成 PDF → 浏览器下载
- **分享图片**：html2canvas 截图 → 下载 PNG

### 9.10 P2：聊天界面整体美化

#### 9.10.1 配色方案

```
主背景：     stone-50  (#FAFAF9)  — 暖白
卡片/气泡：   white     (#FFFFFF)  — 消息气泡
侧边栏：     stone-100 (#F5F5F4)  — 微暖灰
主文字：     stone-800 (#292524)  — 柔和黑
品牌色：     amber-500 (#F59E0B)  — 旅行暖橙
辅助色：     emerald-500 (#10B981) — 成功状态
用户气泡：   amber-500 → amber-600 微渐变
AI 气泡：    white + stone-100 边框 + 微阴影
```

#### 9.10.2 布局重构

```
┌──────┬───────────────────────────────────┐
│      │  TravelMate 智游伴    ☀️ 深圳 26° │
│ 会话 ├───────────────────────────────────┤
│ 侧边 │                                   │
│ 栏   │       消息列表（max-w-3xl）        │
│      │       居中，视觉聚焦               │
│      │                                   │
│      ├───────────────────────────────────┤
│      │       输入框（max-w-3xl）          │
└──────┴───────────────────────────────────┘
```

#### 9.10.3 消息气泡

**用户气泡**：`bg-gradient-to-r from-amber-500 to-amber-600`，`text-white`，`rounded-2xl rounded-br-md`，右对齐，max-w-[70%]

**AI 气泡**：`bg-white` + `border-stone-100` + `shadow-sm`，`text-stone-800`，`rounded-2xl rounded-bl-md`，左对齐，max-w-[75%]

**间距**：`space-y-6`（宽松呼吸感）

#### 9.10.4 暗色模式

Tailwind `@variant dark (&:where(.dark, .dark *))`：

| 元素 | 浅色 | 暗色 |
|------|------|------|
| 主背景 | stone-50 | stone-900 |
| 卡片 | white | stone-800 |
| 侧边栏 | stone-100 | stone-900 |
| 文字 | stone-800 | stone-100 |
| 边框 | stone-200 | stone-700 |

**后端重启检测**：`GET /startup-ts` 返回启动时间戳，前端 onMounted 比较 localStorage 中的时间戳，不一致则重置为浅色模式。

#### 9.10.5 欢迎页（空状态）

```
┌─────────────────────────────────────┐
│            🗺️                       │
│        TravelMate                   │
│       你的 AI 旅行伙伴               │
│                                     │
│  ┌─────────────────────────────┐    │
│  │  🌤️ 深圳 今天晴 26°C       │    │
│  └─────────────────────────────┘    │
│                                     │
│  [🗺️ 规划行程] [🌤️ 查天气] [🏯 推荐]│
│                                     │
│  或直接输入你想去的地方...           │
└─────────────────────────────────────┘
```

### 9.11 P2：首页天气 + 会话启动问候

#### 9.11.1 首页天气

Header 右侧显示实时天气（三层定位 + 30 分钟自动刷新）：
```
☀️ 深圳 26°C
```

天气图标映射：晴→☀️，多云/阴→⛅，雨/雷→🌧️，雪→❄️，风→💨

#### 9.11.2 会话启动问候

空会话时自动调用 `GET /proactive/greet`，LLM 生成个性化开场白：

**新用户**：
> 👋 早上好！你目前在杭州，今天小雨 22°C，出门记得带伞。
> 我是你的旅行助手，可以帮你规划行程、查天气、推荐美食。
> 最近有想去的地方吗？

**回访用户**：
> 👋 下午好！深圳今天晴 28°C。
> 上次你规划的大理行程还没做完呢，要接着完善吗？我知道你不吃辣，会帮你留意清淡餐厅。

### 9.12 P3：知识库自动调研

#### 9.12.1 搜索层实现

```python
from duckduckgo_search import DDGS

SEARCH_TEMPLATES = {
    "attractions": lambda d: f"{d} 必去景点 旅游攻略",
    "history": lambda d: f"{d} 历史文化 典故 名胜古迹",
    "food": lambda d: f"{d} 特色美食 推荐 必吃",
    "tips": lambda d: f"{d} 旅游注意事项 交通 最佳季节",
}
```

#### 9.12.2 LLM 策展 Prompt

将搜索结果精炼为标准 Markdown 攻略文档（800-1500 字），包含：
- 简介、历史文化、经典景观、美食推荐、游玩建议
- 去除广告和无关信息，语言生动有趣

#### 9.12.3 知识库管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/knowledge/auto-expand` | 手动触发单景点调研 |
| POST | `/knowledge/auto-expand-batch` | 批量扩充（SSE 进度推送） |
| GET | `/knowledge/has-local` | 检查是否有本地知识 |

### 9.13 P3：行程风格对比

#### 9.13.1 后端改动

- `schemas.py`：ChatRequest 新增 `trip_style` 字段
- `trip_prompts.py`：新增 `STYLE_INSTRUCTIONS` 字典 + `{style_instructions}` 占位符
- `trip_service.py`：`generate_trip_plan()` 新增 `style` 参数
- `intent_router.py`：透传 `trip_style`
- `chat.py`：metadata 加入 `trip_style`

#### 9.13.2 前端改动

- **StyleSelector.vue**（新建）：3 个风格 chip 按钮
- **ChatInput.vue**：旅行关键词正则检测 → 条件显示 StyleSelector
- **chat.ts**：`sendMessage()` 新增 `tripStyle` 参数
- **ChatContainer.vue**：风格切换逻辑（switchStyle 事件链）
- **TripCard.vue**：风格标签 + "换种风格"按钮

### 9.14 优化方案测试预期与结果

#### 9.14.1 P0 TripCard 行程卡片测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 结构化渲染 | 发送"规划杭州3天行程" | TripCard 多标签卡片（行程总览 + Day1/2/3） | JSON 解析成功，Pydantic 校验通过 |
| Tab 切换 | 点击 "Day 2" 标签 | 显示第二天行程时间轴 | 主题 + 景点列表 + 餐饮 + 住宿 |
| 风格切换 | 点击"换种风格" → 选 compact | 生成紧凑型行程卡片 | STYLE_INSTRUCTIONS 注入，新卡片替换 |
| JSON 容错（正则提取） | LLM 输出混有非 JSON 文本 | 正则提取 `{...}` 后成功解析 | Fallback 1 生效 |
| JSON 容错（降级） | LLM 输出完全无法解析 | 降级为 Markdown 渲染 | Fallback 2 生效 |
| 换页不丢数据 | 切换 Tab 后切回来 | 数据保持不变 | 响应式状态正确 |
| 预算显示 | 行程含 budget 字段 | 显示预算拆分（交通/餐饮/住宿/门票） | budget 字段渲染 |
| tips 显示 | 行程含 tips 数组 | 显示旅行小贴士列表 | tips 数组渲染 |

#### 9.14.2 P0 KNOWLEDGE 兜底逻辑测试

| 测试场景 | 输入 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 知识库命中 | "西湖有什么历史" | 基于知识库的导游式回答 | 正常路径，Context 注入 |
| 检索为空 | "平遥古城有什么" | 自动调研 → 回答 | 兜底 3 触发，含"🔍"前缀 |
| 通用知识兜底 | "什么是背包旅行" | LLM 通用知识 + 诚实标注 | 兜底 1 生效 |
| 误匹配兜底 | "北京长城"匹配到"西安城墙" | 低置信度标记，LLM 可忽略 | 兜底 2 生效 |
| 纠正闭环 | "不对，灵隐寺是东晋建的" | 更新知识库 + 确认回复 | correct_knowledge 触发 |

#### 9.14.3 P0 会话管理测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 创建会话 | 点击 + 按钮 | 新会话出现在列表顶部 | POST /sessions 成功 |
| 切换会话 | 点击另一个会话 | 消息列表刷新，左侧高亮切换 | GET /messages 返回正确数据 |
| 删除会话 | hover → 点击 × | 会话从列表移除 | DELETE 成功，数据库级联删除 |
| 双击重命名 | 双击标题 → 输入新名称 → Enter | 标题更新 | PUT /rename 成功 |
| Esc 取消重命名 | 重命名中按 Esc | 恢复原标题 | cancelRename 生效 |
| 会话自动命名 | 发送"杭州3天行程" | 标题自动设为"杭州·3日游" | chat.py 自动命名逻辑 |
| 首条消息命名 | 新会话发"帮我查天气" | 标题截取前 15 字 | _generate_title 生效 |
| TripCard 恢复 | 切换会话后切回含行程的会话 | TripCard 正确渲染 | metadata.trip_plan 恢复 |

#### 9.14.4 P0 偏好管理面板测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 查看偏好 | 打开偏好面板 | 分类展示所有偏好 | GET /preferences 返回正确数据 |
| 手动添加 | 选择 category → 输入 key/value → 保存 | 新偏好出现在列表 | POST 成功，ChromaDB + SQLite 双写 |
| 删除偏好 | 点击删除按钮 | 偏好从列表移除 | DELETE 成功 |
| 分类筛选 | 点击"饮食"分类 | 只显示饮食类偏好 | 前端过滤生效 |

#### 9.14.5 P1 错误恢复与重试测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 网络断开 | 断网后发送消息 | 显示红色错误 + "重新发送"按钮 | NetworkError 检测 |
| 服务器 500 | 后端返回 500 | 显示"服务器异常" + 重试按钮 | ServerError 检测 |
| 超时 | 请求超时 | 显示"请求超时" + 重试按钮 | TimeoutError 检测 |
| 重试成功 | 点击"重新发送" | 消息重新发送，成功后恢复 | 重试逻辑正确 |
| 连续失败 | 重试 3 次仍失败 | 提示"请检查后端是否启动" | 连续失败计数 |

#### 9.14.6 P1 消息操作菜单测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 复制文本 | 右键 → 复制文本 | 内容复制到剪贴板 | clipboard API 调用 |
| 重新生成 | 右键 assistant 消息 → 重新生成 | 重新发送对应 user 消息 | 找到前一条 user 消息 |
| 删除消息 | 右键 → 删除 | 消息从列表和数据库移除 | DELETE API 调用 |
| 播报消息 | 右键 assistant 文本 → 播报 | TTS 朗读消息内容 | useSpeechSynthesis.speak() |

#### 9.14.7 P1 行程导出测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 导出 PDF | 点击"导出 PDF"按钮 | 浏览器下载 PDF 文件 | ReportLab 生成，含行程详情 |
| 导出图片 | 点击"分享图片"按钮 | 浏览器下载 PNG 截图 | html2canvas 截图，含完整卡片 |
| 空行程导出 | 行程数据为空 | 不崩溃，提示无内容 | 边界处理 |

#### 9.14.8 P2 界面美化 + 天气 + 问候测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 暗色模式切换 | 点击暗色模式按钮 | 全局切换 stone-900 背景 | Tailwind dark variant 生效 |
| 后端重启检测 | 重启后端后刷新页面 | 自动重置为浅色模式 | startup-ts 比较生效 |
| 首页天气 | 打开空会话 | Header 显示天气（如"☀️ 深圳 26°C"） | 三层定位 + 天气查询 |
| 30 分钟刷新 | 等待 30 分钟 | 天气数据自动更新 | 定时器刷新 |
| 会话问候 | 打开空会话 | 显示个性化问候语 | /proactive/greet 调用成功 |
| 欢迎页 | 无消息时 | 显示 TravelMate logo + 快捷按钮 | 空状态组件渲染 |
| 用户气泡 | 发送消息 | amber 渐变 + 圆角 + 右对齐 | Tailwind 样式正确 |
| AI 气泡 | 接收回复 | 白色 + 边框 + 阴影 + 左对齐 | Tailwind 样式正确 |

#### 9.14.9 P3 知识库自动调研测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 单景点调研 | POST /knowledge/auto-expand | 生成 .md 文件 + 向量化入库 | chunk_count > 0 |
| 批量调研 | POST /knowledge/auto-expand-batch | SSE 逐个推送进度 | 每景点独立处理 |
| 已有知识跳过 | 调研已有知识的景点 | 不重复生成 | has_local_knowledge 检查 |
| 纠正反馈 | "不对，XX 是 YY 建的" | 更新 .md + 重新向量化 | correct_knowledge 闭环 |
| LLM 失败降级 | 模拟 LLM 返回空 | status: generate_failed | 不崩溃 |
| 前端标签 | 消息含自动调研标记 | 显示绿色"🔍 已自动调研"标签 | metadata 检测 |

#### 9.14.10 P3 行程风格对比测试

| 测试场景 | 操作 | 预期结果 | 验证要点 |
|----------|------|----------|----------|
| 默认风格 | 不选风格直接规划 | 生成标准行程 | style="default" |
| compact 风格 | 选紧凑型 → 规划 | 景点密集，时间紧凑 | STYLE_INSTRUCTIONS.compact 注入 |
| leisure 风格 | 选休闲型 → 规划 | 景点较少，节奏舒缓 | STYLE_INSTRUCTIONS.leisure 注入 |
| culture 风格 | 选文化型 → 规划 | 偏重博物馆/历史景点 | STYLE_INSTRUCTIONS.culture 注入 |
| 风格 chip 显示 | 输入旅行关键词 | StyleSelector 出现在输入框上方 | 正则检测旅行意图 |
| 风格 chip 隐藏 | 输入非旅行消息 | StyleSelector 隐藏 | 条件渲染 |
| TripCard 风格标签 | 查看行程卡片 | 显示当前风格标签 | metadata.trip_style 渲染 |
| 换风格按钮 | 点击"换种风格" | 重新生成行程（新风格） | switchStyle 事件链 |

---

## 十、附录

### 附录 A：完整目录结构

见 [2.2 目录结构](#22-目录结构)。

### 附录 B：关键技术方案详解

#### B.1 三级意图识别 vs 单一 LLM

| 维度 | 三级管道 | 单一 LLM |
|------|----------|----------|
| 简单消息延迟 | <10ms（正则） | 300ms+（每次调 LLM） |
| 成本 | 正则免费，AI 层按需调用 | 每条消息都消耗 token |
| 安全 | 代码级强制过滤 | 依赖 LLM 自律 |
| 准确率 | 正则 100% + AI 95%+ | LLM ~90% |

#### B.2 ChromaDB + SQLite 双存储

- **SQLite**：结构化查询（"该用户所有饮食偏好"）、统计分析、精确 CRUD
- **ChromaDB**：语义相似度搜索（"用户提到海鲜相关的偏好"）、上下文注入
- **双写策略**：`save_memory()` 同时写入两端，保证一致性

#### B.3 APScheduler vs Celery

选择 APScheduler：
- 轻量级，无需独立 Worker 进程
- 原生支持 async/await
- 适合单机部署场景
- 定时任务（天气提醒）+ 一次性任务（到达问候）均支持

#### B.4 知识库自动调研 vs 手动维护

| 维度 | 自动调研 | 手动维护 |
|------|----------|----------|
| 覆盖速度 | 数秒生成一份 | 需人工编写 |
| 质量 | 依赖搜索结果 | 高质量但耗时 |
| 扩展性 | 可批量扩充 15+ 城市 | 线性增长 |
| 一致性 | 可能含噪音 | 精准可控 |

最佳实践：自动调研快速覆盖 → 用户反馈纠正 → 逐步提升质量

### 附录 C：里程碑验收总表

| 阶段 | 内容 | 预估工期 |
|------|------|----------|
| 阶段 0-2 | 工程脚手架 + 前端界面 + 后端 API | 5-8 天 |
| 阶段 3-4 | 意图识别管道 + 记忆系统 | 7-9 天 |
| 阶段 5-7 | 地图/天气集成 + 行程生成 + RAG 知识 | 7-10 天 |
| 阶段 8-9 | 主动服务 + 前后端大串联 | 6-8 天 |
| 阶段 10-12 | 安全系统 + 语音交互 + 联调部署 | 6-10 天 |
| **总计** | | **31-45 天** |

### 附录 D：优化方案文件清单

#### D.1 P0 修改文件

| 文件 | 改动 | 说明 |
|------|------|------|
| `backend/app/services/rag_service.py` | 改造 | 双层兜底 + 自动调研触发 |
| `backend/app/utils/trip_prompts.py` | 重写 | Prompt 从 Markdown 改为 JSON |
| `backend/app/services/trip_service.py` | 改造 | JSON 解析 + Pydantic 校验 + 风格参数 |
| `backend/app/api/chat.py` | 小改 | metadata 增强 + 自动命名 |
| `backend/app/api/sessions.py` | 小改 | metadata JSON 解析 + 标题更新 |
| `backend/app/services/context_service.py` | 小改 | save_message 支持 metadata |
| `backend/app/models/database.py` | 小改 | ALTER TABLE metadata |
| `frontend/src/components/chat/TripCard.vue` | 重写 | 多标签结构化卡片 |
| `frontend/src/components/chat/ChatContainer.vue` | 改造 | 布局重构 + 侧边栏集成 |
| `frontend/src/stores/chat.ts` | 改造 | 会话管理 + metadata 映射 |
| `frontend/src/components/chat/SessionSidebar.vue` | 新建 | 会话侧边栏 |
| `frontend/src/components/chat/PreferencePanel.vue` | 新建 | 偏好管理面板 |

#### D.2 P1 修改文件

| 文件 | 改动 | 说明 |
|------|------|------|
| `frontend/src/stores/chat.ts` | 小改 | 错误类型区分 + 重试逻辑 |
| `frontend/src/components/chat/MessageBubble.vue` | 小改 | 右键菜单 + 重试按钮 |
| `backend/app/services/export_service.py` | 小改 | PDF/图片导出 API |
| `backend/app/api/trip.py` | 小改 | 导出端点 |

#### D.3 P2 修改文件

| 文件 | 改动 | 说明 |
|------|------|------|
| `frontend/src/components/chat/ChatContainer.vue` | 小改 | 天气组件 + 欢迎页 + 美化 |
| `frontend/src/components/chat/MessageBubble.vue` | 改造 | 新气泡样式 + 渐变 + 暗色 |
| `frontend/src/components/chat/ChatInput.vue` | 改造 | 新输入框样式 + 动态 placeholder |
| `frontend/src/style.css` | 改造 | 全局样式 + 滚动条 + prose |
| `frontend/src/App.vue` | 小改 | dark class 管理 |
| `backend/app/api/weather.py` | 新增 | GET /weather/current |
| `backend/app/api/proactive.py` | 改造 | GET /proactive/greet |
| `backend/app/services/proactive_service.py` | 小改 | 天气定位辅助函数 |
| `backend/app/services/checklist_service.py` | 新增 | 旅行准备清单生成 |

#### D.4 P3 修改文件

| 文件 | 改动 | 说明 |
|------|------|------|
| `backend/app/services/knowledge_expander.py` | **新增** | 自动调研管线 |
| `backend/app/api/knowledge.py` | **新增** | 知识库管理 API |
| `backend/requirements.txt` | 小改 | 新增 duckduckgo-search |
| `backend/app/main.py` | 小改 | 注册 knowledge_router |
| `backend/app/models/schemas.py` | 小改 | ChatRequest 新增 trip_style |
| `backend/app/utils/trip_prompts.py` | 小改 | STYLE_INSTRUCTIONS |
| `frontend/src/components/chat/StyleSelector.vue` | **新建** | 风格选择器 |
| `frontend/src/components/chat/BatchExpandModal.vue` | **新建** | 批量扩充弹窗 |
| `frontend/src/components/chat/MessageBubble.vue` | 小改 | 自动调研标签 |

### 附录 E：P3 依赖安装

```bash
# 在 backend/venv 虚拟环境中执行
pip install duckduckgo-search>=6.0.0

# 安装后验证
python -c "from duckduckgo_search import DDGS; print('OK')"
```

安装成功的额外依赖：
- `duckduckgo-search==8.1.1`
- `primp==1.2.3`（HTTP 客户端）
- `lxml==6.1.0`（XML 解析）

### 附录 F：已知限制与后续优化

| 功能 | 限制 | 优化方向 |
|------|------|----------|
| 景点名称提取 | 简单正则，对复杂句子可能不准确 | LLM 提取或 NER 模型 |
| 策展质量 | 依赖搜索结果，冷门景点结果少 | 多搜索引擎轮询 |
| 缓存一致性 | 手动编辑 .md 后 ChromaDB 不自动更新 | 文件监听或定期重载 |
| 搜索限流 | DuckDuckGo 有频率限制 | Redis/TTL 缓存 |
| 风格样式 | 只有 3 种预设 | 用户自定义风格组合 |
| 语音交互 | 仅支持普通话 | 扩展方言 + 多语言 |
| 安全检查 | 基于关键词列表 | 引入 LLM 语义级安全判断 |

### 附录 G：架构决策记录

| 决策 | 选择 | 替代方案 | 理由 |
|------|------|----------|------|
| 意图识别 | 三级管道（正则→AI→安全） | 单一 LLM | 速度 + 成本 + 安全 |
| 数据存储 | SQLite + ChromaDB | 纯 PostgreSQL | 轻量部署，无需额外服务 |
| 前端状态 | Pinia | Redux/Vuex | Vue 3 官方推荐，组合式 API |
| 样式方案 | Tailwind CSS v4 | CSS Modules/SCSS | 快速开发，暗色模式原生支持 |
| 定时任务 | APScheduler | Celery | 轻量，无需独立 Worker |
| 知识搜索 | DuckDuckGo | Google/Bing API | 免费，无需 API Key |
| LLM | DeepSeek | OpenAI/Claude | 中文优化好，成本低 |
| 地图 | 高德 | 百度/腾讯 | POI 数据全面，API 稳定 |
| 设备标识 | localStorage UUID | 用户名+密码 | 零摩擦上手，无需注册 |

### 附录 H：综合测试验证总表

| 模块 | 测试项数 | 核心场景 | 通过标准 |
|------|----------|----------|----------|
| 一、项目基础 | 3 | 启动、CORS、暗色模式 | 前后端正常启动，跨域允许，dark mode 切换 |
| 三、意图识别管道 | 6 | 正则匹配、AI 识别、安全拦截、上下文延续、代词消解、异常降级 | 各意图正确分类，安全检查生效，JSON 解析失败时降级为 CHAT |
| 四、前端状态管理 | 4 | 消息发送、会话切换、TripCard 恢复、错误处理 | 乐观更新正常，metadata 映射正确，重试逻辑生效 |
| 五、安全与记忆 | 6 | 三级安全、频率限制、双引擎记忆、向量查询、SQLite 兜底 | BLOCK/URGENT/WARN 正确触发，ChromaDB + SQLite 双写一致 |
| 六、外部集成 | 15 | 天气查询、行程规划、RAG 检索、自动调研、纠正闭环、会话命名 | 各服务正常调用，兜底逻辑生效，自动调研生成 .md 并向量化 |
| 七、主动服务与安全 | 14 | WS 连接/推送/断连、个性化问候、天气提醒、到达问候、安全检查、频率限制 | 推送到达设备，定时任务正确调度，安全过滤生效 |
| 八、语音交互 | 6 | ASR 识别、TTS 播报、Markdown 清理、权限拒绝、静默停止、连续播报 | Web Speech API 正常工作，边界情况不崩溃 |
| 九、优化方案 P0 | 16 | TripCard 结构化、KNOWLEDGE 兜底、会话管理、偏好面板 | JSON 解析 + Pydantic 校验，双层兜底生效，会话 CRUD 完整 |
| 九、优化方案 P1 | 10 | 错误恢复/重试、消息右键菜单、行程导出 | 错误类型区分正确，重试逻辑生效，PDF/PNG 导出成功 |
| 九、优化方案 P2 | 8 | 界面美化、暗色模式、首页天气、欢迎页、会话问候 | Tailwind 样式正确，天气数据实时，问候个性化 |
| 九、优化方案 P3 | 10 | 自动调研、风格对比、style chip、换风格按钮 | 调研生成 + 向量化，4 种风格差异明显，事件链完整 |
| **总计** | **98** | | |

### 附录 I：UML 设计图

> 以下 UML 图使用 Mermaid 语法编写，可在 GitHub、Typora、VS Code 等工具中直接渲染。

#### I.1 用例图（Use Case Diagram）

```mermaid
graph TB
    User([游客 User])
    LLM([DeepSeek LLM])
    MapAPI([高德地图 API])
    DDG([DuckDuckGo])

    subgraph System["AI智游伴系统"]
        UC1[自然语言对话]
        UC2[行程规划]
        UC3[天气查询]
        UC4[景点知识问答]
        UC5[偏好记忆管理]
        UC6[语音输入]
        UC7[语音播报]
        UC8[行程风格对比]
        UC9[行程导出]
        UC10[会话管理]
        UC11[知识库自动调研]
        UC12[用户纠正反馈]
        UC13[定时天气提醒]
        UC14[到达景点问候]
        UC15[个性化开场问候]
    end

    User --- UC1
    User --- UC2
    User --- UC3
    User --- UC4
    User --- UC5
    User --- UC6
    User --- UC7
    User --- UC8
    User --- UC9
    User --- UC10
    User --- UC12

    UC2 -.->|include| LLM
    UC3 -.->|include| MapAPI
    UC4 -.->|include| LLM
    UC11 -.->|include| DDG
    UC11 -.->|include| LLM
    UC13 -.->|include| MapAPI
    UC14 -.->|include| LLM
    UC15 -.->|include| LLM

    UC2 -.->|extend| UC8
    UC4 -.->|extend| UC11
    UC4 -.->|extend| UC12
    UC3 -.->|extend| UC13
```

**用例说明**：

| 用例 | 参与者 | 描述 |
|------|--------|------|
| 自然语言对话 | 游客 → 系统 | 游客通过文本或语音输入与 AI 助手对话 |
| 行程规划 | 游客 → 系统 → LLM | 输入目的地和天数，AI 生成结构化多日行程 |
| 天气查询 | 游客 → 系统 → 高德 API | 查询指定城市的实时天气和预报 |
| 景点知识问答 | 游客 → 系统 → LLM | RAG 检索知识库回答景点相关问题 |
| 偏好记忆管理 | 游客 → 系统 | 设置、查询、删除个人旅行偏好 |
| 语音输入/播报 | 游客 → 系统 | Web Speech API 实现语音识别和 TTS |
| 行程风格对比 | 游客 → 系统 → LLM | 同一目的地生成紧凑/休闲/文化三种风格对比 |
| 知识库自动调研 | 系统 → DuckDuckGo → LLM | 知识库无匹配时自动搜索、策展、入库 |
| 用户纠正反馈 | 游客 → 系统 | 用户指出错误信息，系统自动更新知识库 |
| 定时天气提醒 | 系统 → 高德 API | 每日定时检查天气，有雨时推送提醒 |
| 个性化开场问候 | 系统 → LLM | 根据用户画像和天气生成个性化问候语 |

#### I.2 类图（Class Diagram）

```mermaid
classDiagram
    direction TB

    class ChatRequest {
        +String message
        +String device_id
        +String session_id
        +String trip_style
    }

    class ChatResponse {
        +String reply
        +String intent
        +String message_type
        +Dict metadata
    }

    class IntentRouter {
        -Regex _INTRO_RE
        -Regex _RECALL_RE
        -Regex _CORRECTION_RE
        +route_intent(msg, device_id, session_id, style) Dict
        -_get_user_preferences(device_id) String
    }

    class RegexMatcher {
        +regex_match(text) Tuple
    }

    class MemoryService {
        +save_memory(device_id, category, key, value) bool
        +query_memory(device_id, query_text, top_k) List
        +get_all_preferences(device_id) List
        +delete_preference(device_id, category, key) bool
    }

    class TripService {
        +generate_trip_plan(device_id, dest, days, style) Dict
        +query_trip_plans(device_id, limit) List
        -_parse_trip_json(raw, dest) Dict
        -_save_trip_to_db(device_id, dest, days, json)
    }

    class RAGService {
        +query_knowledge(question, spot_name) String
        -retrieve_knowledge(query, spot_name, top_k) List
    }

    class KnowledgeExpander {
        +auto_expand(spot_name) Dict
        +correct_knowledge(message) Dict
        +has_local_knowledge(spot_name) bool
        -_generate_knowledge(spot_name) String
        -_vectorize_single(name, content) int
    }

    class WeatherService {
        +get_weather_forecast(city) Dict
    }

    class MapService {
        +search_places(keyword, city) List
    }

    class ProactiveService {
        -Dict _connections
        -Scheduler _scheduler
        +register_ws(device_id, ws)
        +push_message(device_id, content, type) bool
        +generate_greeting(device_id) Dict
        +set_weather_reminder(device_id, city, hour) String
        +send_arrival_greeting(device_id, spot, city) String
    }

    class SafetyChecker {
        -List BLOCK_KEYWORDS
        -List WARN_KEYWORDS
        -List URGENT_KEYWORDS
        +input_safety_check(text) Dict
        +output_safety_check(text) Dict
        +filter_llm_output(text) String
        +check_rate_limit(device_id) bool
    }

    class ContextService {
        +save_message(device_id, session, role, content, intent, metadata)
        +get_recent_history(device_id, session, limit) List
    }

    class LLMClient {
        +call_llm(messages, system_prompt, temperature, max_tokens) String
    }

    class Itinerary {
        +String trip_id
        +String destination
        +String summary
        +List days
        +float estimated_budget
        +BudgetBreakdown budget_breakdown
        +List tips
    }

    class DayPlan {
        +int day_index
        +String theme
        +List spots
        +List meals
        +HotelItem hotel
    }

    class SpotItem {
        +String name
        +String start_time
        +String end_time
        +String description
        +float estimated_cost
    }

    IntentRouter --> RegexMatcher : 第一层
    IntentRouter --> LLMClient : 第二层 AI
    IntentRouter --> SafetyChecker : 第三层
    IntentRouter --> MemoryService : 读取偏好
    IntentRouter --> ContextService : 获取历史
    IntentRouter --> TripService : TRIP_PLAN
    IntentRouter --> WeatherService : WEATHER
    IntentRouter --> RAGService : KNOWLEDGE

    TripService --> MapService : POI 搜索
    TripService --> WeatherService : 天气数据
    TripService --> LLMClient : 生成行程
    TripService --> MemoryService : 用户偏好

    RAGService --> KnowledgeExpander : 自动调研
    RAGService --> LLMClient : 生成回答

    ProactiveService --> WeatherService : 天气检查
    ProactiveService --> MemoryService : 用户偏好
    ProactiveService --> LLMClient : 生成问候

    Itinerary *-- DayPlan : 包含
    DayPlan *-- SpotItem : 包含
```

#### I.3 时序图（Sequence Diagram）

**行程规划完整交互流程**：

```mermaid
sequenceDiagram
    autonumber
    actor U as 游客
    participant FE as 前端 (Vue 3)
    participant API as API Gateway
    participant IR as IntentRouter
    participant SC as SafetyChecker
    participant RM as RegexMatcher
    participant LLM as DeepSeek LLM
    participant TS as TripService
    participant MS as MapService
    participant WS as WeatherService
    participant MEM as MemoryService
    participant CTX as ContextService
    participant DB as SQLite

    U->>FE: 输入"帮我规划杭州3天行程"
    FE->>API: POST /chat {message, device_id, session_id}
    
    API->>SC: input_safety_check(text)
    SC-->>API: {passed: true, level: SAFE}
    
    API->>RM: regex_match(text)
    RM-->>API: null (未命中正则)
    
    API->>IR: route_intent(message, device_id, session_id)
    
    IR->>CTX: get_recent_history(device_id, limit=6)
    CTX->>DB: SELECT * FROM conversations
    DB-->>CTX: [最近6条消息]
    CTX-->>IR: history
    
    IR->>MEM: get_all_preferences(device_id)
    MEM->>DB: SELECT * FROM preferences
    DB-->>MEM: [饮食偏好, 预算偏好...]
    MEM-->>IR: prefs
    
    IR->>LLM: call_llm(intent_prompt + history + prefs)
    LLM-->>IR: {intent: "TRIP_PLAN", destination: "杭州", days: 3}
    
    IR->>TS: generate_trip_plan(device_id, "杭州", 3, "default")
    
    par 并行数据收集
        TS->>MS: search_places("杭州景点")
        MS-->>TS: [西湖, 灵隐寺, 西溪湿地...]
    and
        TS->>WS: get_weather_forecast("杭州")
        WS-->>TS: {days: [{day_weather: "晴", day_temp: 28}...]}
    and
        TS->>MEM: get_all_preferences(device_id)
        MEM-->>TS: [不吃辣, 预算中等...]
    end
    
    TS->>LLM: call_llm(trip_plan_prompt + POI + 天气 + 偏好)
    LLM-->>TS: JSON 行程数据
    
    TS->>TS: _parse_trip_json() → Itinerary 校验
    TS->>DB: INSERT INTO trips (目的地, 行程JSON)
    TS-->>IR: {summary: "杭州3日游行程...", itinerary_json: {...}}
    
    IR-->>API: {intent: "TRIP_PLAN", reply: summary, extracted: {_trip_plan: ...}}
    
    API->>SC: filter_llm_output(reply)
    SC-->>API: reply (安全)
    
    API->>CTX: save_message(user + assistant)
    API->>API: 自动命名会话 "杭州·3日游"
    API-->>FE: ChatResponse {reply, intent: "TRIP_PLAN", metadata: {trip_plan: {...}}}
    
    FE->>FE: message_type = "card"
    FE->>U: 渲染 TripCard 结构化卡片（行程总览 + Day1/2/3 Tab）
```

**意图识别上下文延续流程**：

```mermaid
sequenceDiagram
    autonumber
    actor U as 游客
    participant FE as 前端
    participant API as API Gateway
    participant IR as IntentRouter
    participant LLM as DeepSeek LLM

    Note over U,LLM: 第一轮：正常天气查询
    U->>FE: "查询杭州的天气"
    FE->>API: POST /chat
    API->>IR: route_intent("查询杭州的天气", ...)
    IR->>LLM: intent_prompt + 用户消息
    LLM-->>IR: {intent: "WEATHER", city: "杭州"}
    IR-->>API: reply: "杭州今天晴，28°C..."
    API-->>FE: {intent: "WEATHER", reply: "杭州今天晴..."}
    FE->>U: 显示天气卡片

    Note over U,LLM: 第二轮：上下文延续（无天气关键词）
    U->>FE: "哈尔滨"
    FE->>API: POST /chat
    API->>IR: route_intent("哈尔滨", ...)
    IR->>IR: get_recent_history(limit=6)
    Note right of IR: 上一轮：用户问天气→助手答天气
    IR->>LLM: intent_prompt + "哈尔滨" + [上下文:天气对话]
    LLM-->>IR: {intent: "WEATHER", city: "哈尔滨"}
    Note right of IR: AI 识别到上下文延续
    IR-->>API: reply: "哈尔滨今天多云，15°C..."
    API-->>FE: {intent: "WEATHER"}
    FE->>U: 显示哈尔滨天气卡片
```

#### I.4 状态图（State Diagram）

**消息状态流转**：

```mermaid
stateDiagram-v2
    [*] --> 用户输入

    用户输入 --> 安全检查中: POST /chat

    安全检查中 --> BLOCK拦截: level=BLOCK
    安全检查中 --> 正则匹配: level=SAFE/WARN/URGENT

    BLOCK拦截 --> 已拒绝: 返回固定拒绝回复
    已拒绝 --> [*]: 存储到 DB

    正则匹配 --> 正则命中: 匹配成功 (<10ms)
    正则匹配 --> AI识别: 未匹配

    正则命中 --> 输出过滤: 直接返回预设回复
    AI识别 --> 输出过滤: 获取意图+回复

    输出过滤 --> 正常返回: output_safety_check 通过
    输出过滤 --> 兜底回复: 检测到不安全内容

    正常返回 --> 消息存储: save_message
    兜底回复 --> 消息存储

    消息存储 --> 前端渲染: ChatResponse
    前端渲染 --> 文本气泡: intent=CHAT
    前端渲染 --> 行程卡片: intent=TRIP_PLAN
    前端渲染 --> 天气卡片: intent=WEATHER
    前端渲染 --> 知识卡片: intent=KNOWLEDGE
```

**会话状态流转**：

```mermaid
stateDiagram-v2
    [*] --> 新建会话: 用户点击 +

    新建会话 --> 首次对话: POST /chat
    新建会话 --> 自动问候: /proactive/greet

    首次对话 --> 自动命名: 截取消息前15字
    自动命名 --> 行程命名: 发送行程规划消息
    行程命名 --> 用户重命名: 双击标题
    用户重命名 --> 自定义命名: Enter 确认

    自定义命名 --> [*]
    自动命名 --> [*]
    行程命名 --> [*]
```

#### I.5 活动图（Activity Diagram）

**知识库自动调研流程**：

```mermaid
flowchart TD
    Start([用户提问景点知识]) --> CheckKnowledge{ChromaDB 检索}

    CheckKnowledge -->|命中| NormalAnswer[注入 Context → LLM 导游式回答]
    CheckKnowledge -->|未命中| CheckLocal{has_local_knowledge?}

    CheckLocal -->|有本地文件| LowConfidence[低置信度标记 → LLM 参考回答]
    CheckLocal -->|无本地文件| AutoExpand[触发自动调研]

    AutoExpand --> Search[DuckDuckGo 搜索景点信息]
    Search --> LLMCuration[LLM 策展：结构化 Markdown]
    LLMCuration --> SaveFile[保存 data/knowledge/景点.md]
    SaveFile --> Vectorize[ChromaDB 向量化入库]
    Vectorize --> ReRetrieval[重新检索知识库]

    ReRetrieval --> CheckAgain{检索结果?}
    CheckAgain -->|命中| AutoAnswer["已自动调研 + LLM 回答"]
    CheckAgain -->|仍为空| FallbackAnswer[LLM 通用知识 + 诚实标注]

    NormalAnswer --> OutputFilter[输出安全过滤]
    LowConfidence --> OutputFilter
    AutoAnswer --> OutputFilter
    FallbackAnswer --> OutputFilter

    OutputFilter --> Return([返回 ChatResponse])
```

**行程生成数据流活动图**：

```mermaid
flowchart LR
    subgraph "输入"
        A[目的地] --> G[行程生成引擎]
        B[天数] --> G
        C[风格] --> G
    end

    subgraph "数据收集（并行）"
        G --> D[高德 POI 搜索]
        G --> E[天气预报查询]
        G --> F[用户偏好读取]
    end

    subgraph "LLM 生成"
        D --> H[组装 Prompt]
        E --> H
        F --> H
        H --> I[DeepSeek 生成 JSON]
    end

    subgraph "校验与存储"
        I --> J{JSON 解析}
        J -->|成功| K[Pydantic 校验]
        J -->|失败| L{正则提取}
        L -->|成功| K
        L -->|失败| M[降级为 Markdown]
        K --> N[存储 SQLite]
    end

    subgraph "输出"
        N --> O[TripCard 结构化卡片]
        M --> O
    end
```

#### I.6 组件图（Component Diagram）

```mermaid
graph TB
    subgraph Frontend["前端 (Vue 3 + TypeScript)"]
        CC[ChatContainer]
        CB[ChatInput]
        MB[MessageBubble]
        TC[TripCard]
        SS[SessionSidebar]
        PP[PreferencePanel]
        STY[StyleSelector]
        WR[WelcomePage]

        subgraph Composables
            ASR[useSpeechRecognition]
            TTS[useSpeechSynthesis]
        end

        subgraph Store
            CS[chat.ts Pinia Store]
        end
    end

    subgraph Backend["后端 (FastAPI + Python)"]
        subgraph API_Layer["API 层"]
            ChatAPI[chat.py]
            SessionAPI[sessions.py]
            MemoryAPI[memory.py]
            WeatherAPI[weather.py]
            KnowledgeAPI[knowledge.py]
            ProactiveAPI[proactive.py]
            TripAPI[trip.py]
        end

        subgraph Service_Layer["服务层"]
            IntentRouter[intent_router.py]
            TripSvc[trip_service.py]
            RAGSvc[rag_service.py]
            WeatherSvc[weather_service.py]
            MemorySvc[memory_service.py]
            ContextSvc[context_service.py]
            KnowledgeExp[knowledge_expander.py]
            ProactiveSvc[proactive_service.py]
            ExportSvc[export_service.py]
            MapSvc[map_service.py]
        end

        subgraph Infra["基础设施层"]
            Safety[safety.py]
            Regex[regex_matcher.py]
            LLMClient[llm_client.py]
            DB[(SQLite)]
            Chroma[(ChromaDB)]
        end
    end

    subgraph External["外部服务"]
        DeepSeek[DeepSeek LLM]
        Amap[高德地图 API]
        DDG[DuckDuckGo]
    end

    CC --> ChatAPI
    CC --> CS
    CB --> ASR
    TC --> TripAPI
    SS --> SessionAPI

    ChatAPI --> IntentRouter
    IntentRouter --> Regex
    IntentRouter --> Safety
    IntentRouter --> TripSvc
    IntentRouter --> WeatherSvc
    IntentRouter --> RAGSvc
    IntentRouter --> MemorySvc

    TripSvc --> LLMClient
    TripSvc --> MapSvc
    TripSvc --> WeatherSvc
    RAGSvc --> KnowledgeExp
    RAGSvc --> LLMClient
    ProactiveSvc --> WeatherSvc
    ProactiveSvc --> LLMClient

    LLMClient --> DeepSeek
    MapSvc --> Amap
    WeatherSvc --> Amap
    KnowledgeExp --> DDG

    MemorySvc --> DB
    MemorySvc --> Chroma
    ContextSvc --> DB
    RAGSvc --> Chroma
    KnowledgeExp --> Chroma
    KnowledgeExp --> DB
```

---

> **本文档整合了 AI智游伴的完整实现方案（从零到一的 13 个阶段）和优化方案（P0-P3 四级优化），覆盖了系统架构、核心功能、UI 设计、安全体系、优化升级的全部内容。**
